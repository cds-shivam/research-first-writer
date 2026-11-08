#!/usr/bin/env python3
"""Citation verifier: checks that verbatim quotes in the research ledger still exist on their source pages.

Usage:
    python3 scripts/verify_citations.py path/to/06-research-brief.md [--timeout SECONDS] [--delay SECONDS] [--json] [--fail-on-missing] [--fail-on-error]

Parses the Facts ledger table, extracts URLs and quotes, fetches each page, and verifies
that the exact quote still appears. Respects robots.txt. Standard library only.

Exit codes:
    0: verification completed successfully (even if some quotes are missing or unreachable)
    1: verification failed due to an error (with --fail-on-error)
    1: one or more quotes are missing (with --fail-on-missing)
"""
import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.request import Request, urlopen

# Status constants
FOUND = "FOUND"
MISSING = "MISSING"
UNREACHABLE = "UNREACHABLE"
SKIPPED = "SKIPPED"
INVALID = "INVALID"

# Default settings
DEFAULT_TIMEOUT = 30
DEFAULT_DELAY = 1
USER_AGENT = "research-first-writer-citation-verifier/1.0 (+https://github.com/jayanti-prajapati/research-first-writer)"


def parse_ledger(path: str) -> List[Dict[str, str]]:
    """Parse the Facts ledger Markdown table from 06-research-brief.md.
    
    Returns a list of dicts with keys: id, fact, kind, source, credited_to, quote.
    Handles "same" in the Source column by carrying forward the previous URL.
    """
    text = Path(path).read_text(encoding="utf-8")
    
    # Find the Facts ledger section
    lines = text.splitlines()
    in_table = False
    headers = []
    rows = []
    last_url = ""
    
    for line in lines:
        if "## Facts ledger" in line or "Facts ledger" in line:
            in_table = False
            continue
        
        # Look for table header
        if line.strip().startswith("|") and "id" in line.lower() and "source" in line.lower():
            parts = [p.strip() for p in line.split("|")]
            headers = [p for p in parts if p]
            in_table = True
            continue
        
        if in_table:
            if not line.strip().startswith("|") or line.strip().startswith("|---"):
                continue
            
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]  # Remove empty strings
            
            if len(parts) >= 6:  # id, fact, kind, source, credited_to, quote
                url = parts[3]
                # Handle "same" - carry forward the previous URL
                if url.lower() == "same":
                    url = last_url
                else:
                    last_url = url
                
                row = {
                    "id": parts[0],
                    "fact": parts[1],
                    "kind": parts[2],
                    "source": url,
                    "credited_to": parts[4],
                    "quote": parts[5]
                }
                rows.append(row)
    
    return rows


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for comparison: collapse multiple spaces, normalize line breaks."""
    # Replace various whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove spaces before punctuation (common in OCR or certain HTML rendering)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    return text.strip()


def decode_html_entities(text: str) -> str:
    """Decode HTML entities like &amp;, &nbsp;, etc."""
    return html.unescape(text)


def extract_text_from_html(html_content: str) -> str:
    """Extract readable text from HTML by removing tags and decoding entities."""
    # Remove script and style content
    html_content = re.sub(r'<script[^>]*>.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Decode HTML entities
    text = decode_html_entities(text)
    
    # Normalize whitespace
    text = normalize_whitespace(text)
    
    return text


def can_fetch(url: str, timeout: int) -> Tuple[bool, Optional[str]]:
    """Check robots.txt to see if the URL can be fetched.
    
    Returns (can_fetch, error_message). If can_fetch is False, error_message explains why.
    """
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "Invalid URL"
    
    # Construct robots.txt URL
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    try:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        
        if not rp.can_fetch(USER_AGENT, url):
            return False, f"Blocked by robots.txt"
        
        return True, None
    except Exception as e:
        # If robots.txt is unreachable, we allow the fetch (conservative approach)
        # but log it in the result
        return True, f"robots.txt check failed: {e}"


def fetch_page(url: str, timeout: int) -> Tuple[Optional[str], Optional[str]]:
    """Fetch a webpage and return its content.
    
    Returns (content, error_message). If content is None, error_message explains why.
    """
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as response:
            # Handle redirects automatically (urlopen does this)
            # Check for HTTP errors
            if response.status >= 400:
                return None, f"HTTP {response.status}"
            
            content = response.read().decode("utf-8", errors="replace")
            return content, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            return None, "Timeout"
        return None, f"Network error: {e.reason}"
    except Exception as e:
        return None, f"Fetch error: {e}"


def normalize_latex(text: str) -> str:
    r"""Convert LaTeX formatting to plain text.

    Examples:
        $40\%$ -> 40%
        $x$ -> x
    """
    # Remove LaTeX math delimiters and escape sequences
    text = re.sub(r'\$([^$]+)\$', r'\1', text)  # Remove $...$
    text = re.sub(r'\\([%{}_#^&~])', r'\1', text)  # Remove backslash escapes
    text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remove LaTeX commands
    text = re.sub(r'[{}]', '', text)  # Remove curly braces
    return text


def normalize_unicode_punctuation(text: str) -> str:
    """Normalize Unicode punctuation to ASCII equivalents.

    Converts smart quotes and other Unicode punctuation to ASCII.
    """
    # Smart quotes to straight quotes
    text = text.replace('\u2018', "'")  # Left single quotation mark
    text = text.replace('\u2019', "'")  # Right single quotation mark
    text = text.replace('\u201c', '"')  # Left double quotation mark
    text = text.replace('\u201d', '"')  # Right double quotation mark
    text = text.replace('\u2026', '...')  # Ellipsis
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2014', '--')  # Em dash
    return text


def strip_quotes(text: str) -> str:
    """Remove surrounding quotation marks from a string."""
    text = text.strip()
    if len(text) >= 2:
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
    return text


def verify_quote(quote: str, page_content: str, verbose: bool = False) -> bool:
    """Check if the exact quote exists in the page content.

    Args:
        quote: The verbatim quote from the ledger (may include alternatives separated by " / ")
        page_content: The fetched page content (HTML or plain text)
        verbose: If True, print diagnostic information

    Returns:
        True if the quote is found, False otherwise
    """
    if not quote or not quote.strip():
        if verbose:
            print("  [DEBUG] Empty quote")
        return False

    # Extract text from HTML if needed
    if "<" in page_content and ">" in page_content:
        text = extract_text_from_html(page_content)
    else:
        text = page_content

    # Normalize page text (decode entities, normalize whitespace, handle LaTeX, normalize Unicode)
    normalized_page = normalize_whitespace(decode_html_entities(normalize_latex(normalize_unicode_punctuation(text))))

    # Handle alternative quotes separated by " / "
    # The ledger format uses: "Quote A" / "Quote B"
    if " / " in quote:
        alternatives = [strip_quotes(alt.strip()) for alt in quote.split(" / ")]
        if verbose:
            print(f"  [DEBUG] Found {len(alternatives)} alternative quotes")
        for alt in alternatives:
            normalized_alt = normalize_whitespace(decode_html_entities(normalize_latex(normalize_unicode_punctuation(alt))))
            if verbose:
                print(f"  [DEBUG] Trying alternative: {normalized_alt[:80]}...")
            if normalized_alt in normalized_page:
                if verbose:
                    print(f"  [DEBUG] Alternative matched!")
                return True
        if verbose:
            print(f"  [DEBUG] No alternative matched")
        return False

    # Single quote case
    normalized_quote = normalize_whitespace(decode_html_entities(normalize_latex(normalize_unicode_punctuation(strip_quotes(quote)))))

    if verbose:
        print(f"  [DEBUG] Quote length: {len(normalized_quote)}")
        print(f"  [DEBUG] Page text length: {len(normalized_page)}")
        print(f"  [DEBUG] Quote: {normalized_quote[:100]}...")
        print(f"  [DEBUG] Match result: {normalized_quote in normalized_page}")

    # Check for exact match (case-sensitive as quotes should be verbatim)
    return normalized_quote in normalized_page


def verify_citation(row: Dict[str, str], timeout: int, delay: float, index: int, verbose: bool = False) -> Dict[str, any]:
    """Verify a single citation.

    Returns a result dict with status and details.
    """
    url = row.get("source", "").strip()
    quote = row.get("quote", "").strip()
    citation_id = row.get("id", str(index))

    # Validate inputs
    if not url:
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": INVALID,
            "reason": "Empty URL"
        }

    if not quote:
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": INVALID,
            "reason": "Empty quote"
        }

    if verbose:
        print(f"\n[DEBUG] Verifying {citation_id}: {url}")

    # Check robots.txt
    can_fetch_allowed, robots_error = can_fetch(url, timeout)
    if not can_fetch_allowed:
        if verbose:
            print(f"  [DEBUG] robots.txt blocked: {robots_error}")
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": SKIPPED,
            "reason": robots_error
        }

    # Fetch the page
    content, fetch_error = fetch_page(url, timeout)
    if content is None:
        if verbose:
            print(f"  [DEBUG] Fetch failed: {fetch_error}")
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": UNREACHABLE,
            "reason": fetch_error
        }

    if verbose:
        print(f"  [DEBUG] Fetched {len(content)} bytes")

    # Verify the quote
    if verify_quote(quote, content, verbose):
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": FOUND,
            "reason": None
        }
    else:
        return {
            "id": citation_id,
            "url": url,
            "quote": quote,
            "status": MISSING,
            "reason": None
        }


def print_report(results: List[Dict[str, any]]) -> None:
    """Print a human-readable verification report."""
    total = len(results)
    counts = {FOUND: 0, MISSING: 0, UNREACHABLE: 0, SKIPPED: 0, INVALID: 0}
    for r in results:
        counts[r["status"]] += 1
    
    print("\nCitation Verification Report")
    print("=" * 50)
    print(f"\nTotal citations: {total}\n")
    print(f"FOUND: {counts[FOUND]}")
    print(f"MISSING: {counts[MISSING]}")
    print(f"UNREACHABLE: {counts[UNREACHABLE]}")
    print(f"SKIPPED (robots.txt): {counts[SKIPPED]}")
    print(f"INVALID: {counts[INVALID]}")
    
    print("\nResults:")
    print("-" * 50)
    
    for i, r in enumerate(results, 1):
        status = r["status"]
        url = r["url"]
        citation_id = r["id"]
        
        if status == FOUND:
            print(f"[{status}] {citation_id} - {url}")
        elif status == MISSING:
            print(f"[{status}] {citation_id} - {url}")
            print(f"         Expected quote: \"{r['quote']}\"")
        elif status == UNREACHABLE:
            print(f"[{status}] {citation_id} - {url}")
            print(f"         Reason: {r['reason']}")
        elif status == SKIPPED:
            print(f"[{status}] {citation_id} - {url}")
            print(f"         Reason: {r['reason']}")
        elif status == INVALID:
            print(f"[{status}] {citation_id} - {url}")
            print(f"         Reason: {r['reason']}")
    
    print("\n" + "=" * 50)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("ledger", help="Path to 06-research-brief.md")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help=f"HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                    help=f"Delay between requests in seconds (default: {DEFAULT_DELAY})")
    ap.add_argument("--json", action="store_true", help="Output results in JSON format")
    ap.add_argument("--fail-on-missing", action="store_true",
                    help="Return exit code 1 if any quotes are missing")
    ap.add_argument("--fail-on-error", action="store_true",
                    help="Return exit code 1 if any verification errors occur")
    ap.add_argument("--verbose", action="store_true",
                    help="Print diagnostic information for debugging")

    args = ap.parse_args()

    # Parse the ledger
    try:
        rows = parse_ledger(args.ledger)
    except Exception as e:
        print(f"Error parsing ledger: {e}", file=sys.stderr)
        if args.fail_on_error:
            return 1
        return 0

    if not rows:
        print("No citations found in ledger", file=sys.stderr)
        if args.fail_on_error:
            return 1
        return 0

    # Verify each citation
    results = []
    for i, row in enumerate(rows):
        result = verify_citation(row, args.timeout, args.delay, i, args.verbose)
        results.append(result)

        # Add delay between requests (except for the last one)
        if i < len(rows) - 1:
            time.sleep(args.delay)

    # Output results
    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_report(results)

    # Determine exit code
    counts = {status: sum(1 for x in results if x["status"] == status) for status in [FOUND, MISSING, UNREACHABLE, SKIPPED, INVALID]}

    if args.fail_on_error and (counts[INVALID] > 0 or counts[UNREACHABLE] > 0):
        return 1

    if args.fail_on_missing and counts[MISSING] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
