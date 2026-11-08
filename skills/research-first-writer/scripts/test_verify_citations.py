#!/usr/bin/env python3
"""Unit tests for verify_citations.py.

Tests cover ledger parsing, quote verification, HTTP handling, robots.txt,
and CLI behavior. All HTTP requests are mocked.
"""
import json
import sys
import unittest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
from io import StringIO

# Import the module to test
sys.path.insert(0, str(Path(__file__).parent))
import verify_citations as vc


class TestLedgerParsing(unittest.TestCase):
    """Test parsing of the Facts ledger Markdown table."""
    
    def test_valid_ledger_table(self):
        """Test parsing a valid ledger table."""
        content = """# 6. Research brief

## Facts ledger
| id | Fact | Kind | Source | Credited to | Quote (≤ 25 words) |
|---|---|---|---|---|---|
| F1 | Test fact | stat | https://example.com | Author | "test quote here" |
| F2 | Another fact | doc | https://example.org | Source | "another quote" |
"""
        with patch.object(Path, 'read_text', return_value=content):
            rows = vc.parse_ledger("dummy.md")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "F1")
            self.assertEqual(rows[0]["source"], "https://example.com")
            self.assertEqual(rows[0]["quote"], '"test quote here"')
            self.assertEqual(rows[1]["id"], "F2")
    
    def test_missing_ledger_table(self):
        """Test handling when no ledger table is found."""
        content = "# 6. Research brief\n\nNo table here."
        with patch.object(Path, 'read_text', return_value=content):
            rows = vc.parse_ledger("dummy.md")
            self.assertEqual(len(rows), 0)
    
    def test_malformed_table(self):
        """Test handling of malformed table rows."""
        content = """## Facts ledger
| id | Fact | Kind | Source | Credited to | Quote (≤ 25 words) |
|---|---|---|---|---|---|
| F1 | incomplete row
"""
        with patch.object(Path, 'read_text', return_value=content):
            rows = vc.parse_ledger("dummy.md")
            # Should skip malformed rows
            self.assertEqual(len(rows), 0)
    
    def test_same_url_handling(self):
        """Test handling of 'same' in Source column."""
        content = """## Facts ledger
| id | Fact | Kind | Source | Credited to | Quote (≤ 25 words) |
|---|---|---|---|---|---|
| F1 | Test fact | stat | https://example.com | Author | "quote1" |
| F2 | Another fact | doc | same | Source | "quote2" |
| F3 | Third fact | doc | same | Source | "quote3" |
| F4 | Different | doc | https://example.org | Source | "quote4" |
"""
        with patch.object(Path, 'read_text', return_value=content):
            rows = vc.parse_ledger("dummy.md")
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["source"], "https://example.com")
            self.assertEqual(rows[1]["source"], "https://example.com")  # same
            self.assertEqual(rows[2]["source"], "https://example.com")  # same
            self.assertEqual(rows[3]["source"], "https://example.org")  # different


class TestQuoteVerification(unittest.TestCase):
    """Test quote matching logic."""
    
    def test_exact_quote_found(self):
        """Test when exact quote is found in page content."""
        quote = "test quote here"
        content = "This is a page with test quote here in it."
        self.assertTrue(vc.verify_quote(quote, content))
    
    def test_quote_missing(self):
        """Test when quote is not found in page content."""
        quote = "test quote here"
        content = "This page has different content."
        self.assertFalse(vc.verify_quote(quote, content))
    
    def test_html_entity_handling(self):
        """Test HTML entity decoding in quotes."""
        quote = "test &amp; quote"
        content = "This page has test & quote in it."
        self.assertTrue(vc.verify_quote(quote, content))
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization in matching."""
        quote = "test quote here"
        content = "This page has test   quote\n\there in it."
        self.assertTrue(vc.verify_quote(quote, content))
    
    def test_html_to_text_extraction(self):
        """Test extracting text from HTML content."""
        quote = "test quote here"
        content = "<html><body><p>This page has <b>test quote here</b> in it.</p></body></html>"
        self.assertTrue(vc.verify_quote(quote, content))
    
    def test_empty_quote(self):
        """Test handling of empty quote."""
        quote = ""
        content = "Some content"
        self.assertFalse(vc.verify_quote(quote, content))
    
    def test_case_sensitive_matching(self):
        """Test that matching is case-sensitive."""
        quote = "Test Quote"
        content = "This page has test quote in it."
        self.assertFalse(vc.verify_quote(quote, content))

    def test_alternative_quotes(self):
        """Test handling of alternative quotes separated by ' / '."""
        quote = '"Quote A" / "Quote B"'
        content = "This page has Quote B in it."
        self.assertTrue(vc.verify_quote(quote, content))

    def test_alternative_quotes_both_found(self):
        """Test that alternative quotes match if either is found."""
        quote = '"Quote A" / "Quote B"'
        content = "This page has Quote A in it."
        self.assertTrue(vc.verify_quote(quote, content))

    def test_alternative_quotes_none_found(self):
        """Test that alternative quotes fail if neither is found."""
        quote = '"Quote A" / "Quote B"'
        content = "This page has Quote C in it."
        self.assertFalse(vc.verify_quote(quote, content))

    def test_latex_normalization(self):
        """Test LaTeX formatting normalization."""
        quote = "40%"
        content = "This page has $40\\%$ in it."
        self.assertTrue(vc.verify_quote(quote, content))

    def test_latex_complex(self):
        """Test complex LaTeX normalization."""
        quote = "x"
        content = "This page has $x$ in it."
        self.assertTrue(vc.verify_quote(quote, content))

    def test_quote_stripping(self):
        """Test that surrounding quotes are stripped."""
        quote = '"test quote here"'
        content = "This page has test quote here in it."
        self.assertTrue(vc.verify_quote(quote, content))

    def test_quote_stripping_single_quotes(self):
        """Test that surrounding single quotes are stripped."""
        quote = "'test quote here'"
        content = "This page has test quote here in it."
        self.assertTrue(vc.verify_quote(quote, content))


class TestHTTPHandling(unittest.TestCase):
    """Test HTTP request handling with mocks."""
    
    @patch('verify_citations.fetch_page')
    def test_http_404_response(self, mock_fetch):
        """Test handling of HTTP 404 response."""
        mock_fetch.return_value = (None, "HTTP 404")
        row = {"id": "F1", "source": "https://example.com", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.UNREACHABLE)
        self.assertEqual(result["reason"], "HTTP 404")
    
    @patch('verify_citations.fetch_page')
    def test_http_500_response(self, mock_fetch):
        """Test handling of HTTP 500 response."""
        mock_fetch.return_value = (None, "HTTP 500")
        row = {"id": "F1", "source": "https://example.com", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.UNREACHABLE)
        self.assertEqual(result["reason"], "HTTP 500")
    
    @patch('verify_citations.fetch_page')
    def test_request_timeout(self, mock_fetch):
        """Test handling of request timeout."""
        mock_fetch.return_value = (None, "Timeout")
        row = {"id": "F1", "source": "https://example.com", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.UNREACHABLE)
        self.assertEqual(result["reason"], "Timeout")
    
    @patch('verify_citations.fetch_page')
    def test_dns_failure(self, mock_fetch):
        """Test handling of DNS/connection failure."""
        mock_fetch.return_value = (None, "Network error: [Errno -2] Name or service not known")
        row = {"id": "F1", "source": "https://example.com", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.UNREACHABLE)
        self.assertIn("Network error", result["reason"])
    
    @patch('verify_citations.fetch_page')
    def test_successful_fetch_and_match(self, mock_fetch):
        """Test successful fetch with quote found."""
        mock_fetch.return_value = ("This page has test quote here in it.", None)
        row = {"id": "F1", "source": "https://example.com", "quote": "test quote here"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.FOUND)
    
    @patch('verify_citations.fetch_page')
    def test_successful_fetch_no_match(self, mock_fetch):
        """Test successful fetch but quote not found."""
        mock_fetch.return_value = ("This page has different content.", None)
        row = {"id": "F1", "source": "https://example.com", "quote": "test quote here"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.MISSING)


class TestRobotsTxt(unittest.TestCase):
    """Test robots.txt handling."""
    
    @patch('verify_citations.can_fetch')
    def test_robots_txt_disallowed(self, mock_can_fetch):
        """Test when robots.txt disallows the URL."""
        mock_can_fetch.return_value = (False, "Blocked by robots.txt")
        row = {"id": "F1", "source": "https://example.com", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.SKIPPED)
        self.assertEqual(result["reason"], "Blocked by robots.txt")
    
    @patch('verify_citations.can_fetch')
    @patch('verify_citations.fetch_page')
    def test_robots_txt_allowed(self, mock_fetch, mock_can_fetch):
        """Test when robots.txt allows the URL."""
        mock_can_fetch.return_value = (True, None)
        mock_fetch.return_value = ("Content with test quote here", None)
        row = {"id": "F1", "source": "https://example.com", "quote": "test quote here"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.FOUND)


class TestInvalidCitations(unittest.TestCase):
    """Test handling of invalid citation data."""
    
    def test_empty_url(self):
        """Test handling of empty URL."""
        row = {"id": "F1", "source": "", "quote": "test"}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.INVALID)
        self.assertEqual(result["reason"], "Empty URL")
    
    def test_empty_quote(self):
        """Test handling of empty quote."""
        row = {"id": "F1", "source": "https://example.com", "quote": ""}
        result = vc.verify_citation(row, 30, 1, 0)
        self.assertEqual(result["status"], vc.INVALID)
        self.assertEqual(result["reason"], "Empty quote")


class TestCLI(unittest.TestCase):
    """Test CLI behavior and exit codes."""
    
    @patch('verify_citations.parse_ledger')
    @patch('verify_citations.verify_citation')
    @patch('sys.stdout', new_callable=StringIO)
    def test_json_output(self, mock_stdout, mock_verify, mock_parse):
        """Test JSON output format."""
        mock_parse.return_value = [
            {"id": "F1", "source": "https://example.com", "quote": "test", "fact": "f", "kind": "k", "credited_to": "c"}
        ]
        mock_verify.return_value = {
            "id": "F1", "url": "https://example.com", "quote": "test",
            "status": vc.FOUND, "reason": None
        }
        
        with patch('sys.argv', ['verify_citations.py', 'test.md', '--json']):
            exit_code = vc.main()
        
        output = mock_stdout.getvalue()
        results = json.loads(output)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], vc.FOUND)
        self.assertEqual(exit_code, 0)
    
    @patch('verify_citations.parse_ledger')
    @patch('verify_citations.verify_citation')
    @patch('time.sleep')
    @patch('sys.stdout', new_callable=StringIO)
    def test_request_delay(self, mock_stdout, mock_sleep, mock_verify, mock_parse):
        """Test that delay is applied between requests."""
        mock_parse.return_value = [
            {"id": "F1", "source": "https://example.com", "quote": "test", "fact": "f", "kind": "k", "credited_to": "c"},
            {"id": "F2", "source": "https://example.org", "quote": "test2", "fact": "f2", "kind": "k2", "credited_to": "c2"}
        ]
        mock_verify.side_effect = [
            {"id": "F1", "url": "https://example.com", "quote": "test", "status": vc.FOUND, "reason": None},
            {"id": "F2", "url": "https://example.org", "quote": "test2", "status": vc.FOUND, "reason": None}
        ]
        
        with patch('sys.argv', ['verify_citations.py', 'test.md', '--delay', '0.5']):
            exit_code = vc.main()
        
        # Should have called sleep once (between the two requests)
        mock_sleep.assert_called_once_with(0.5)
        self.assertEqual(exit_code, 0)
    
    @patch('verify_citations.parse_ledger')
    @patch('verify_citations.verify_citation')
    @patch('sys.stdout', new_callable=StringIO)
    def test_default_exit_code_on_network_failures(self, mock_stdout, mock_verify, mock_parse):
        """Test that network failures don't cause exit code 1 by default."""
        mock_parse.return_value = [
            {"id": "F1", "source": "https://example.com", "quote": "test", "fact": "f", "kind": "k", "credited_to": "c"}
        ]
        mock_verify.return_value = {
            "id": "F1", "url": "https://example.com", "quote": "test",
            "status": vc.UNREACHABLE, "reason": "HTTP 404"
        }
        
        with patch('sys.argv', ['verify_citations.py', 'test.md']):
            exit_code = vc.main()
        
        self.assertEqual(exit_code, 0)
    
    @patch('verify_citations.parse_ledger')
    @patch('verify_citations.verify_citation')
    @patch('sys.stdout', new_callable=StringIO)
    def test_fail_on_missing(self, mock_stdout, mock_verify, mock_parse):
        """Test --fail-on-missing flag."""
        mock_parse.return_value = [
            {"id": "F1", "source": "https://example.com", "quote": "test", "fact": "f", "kind": "k", "credited_to": "c"}
        ]
        mock_verify.return_value = {
            "id": "F1", "url": "https://example.com", "quote": "test",
            "status": vc.MISSING, "reason": None
        }
        
        with patch('sys.argv', ['verify_citations.py', 'test.md', '--fail-on-missing']):
            exit_code = vc.main()
        
        self.assertEqual(exit_code, 1)
    
    @patch('verify_citations.parse_ledger')
    @patch('verify_citations.verify_citation')
    @patch('sys.stdout', new_callable=StringIO)
    def test_fail_on_error(self, mock_stdout, mock_verify, mock_parse):
        """Test --fail-on-error flag."""
        mock_parse.return_value = [
            {"id": "F1", "source": "https://example.com", "quote": "test", "fact": "f", "kind": "k", "credited_to": "c"}
        ]
        mock_verify.return_value = {
            "id": "F1", "url": "https://example.com", "quote": "test",
            "status": vc.UNREACHABLE, "reason": "HTTP 500"
        }
        
        with patch('sys.argv', ['verify_citations.py', 'test.md', '--fail-on-error']):
            exit_code = vc.main()
        
        self.assertEqual(exit_code, 1)
    
    @patch('verify_citations.parse_ledger')
    @patch('sys.stderr', new_callable=StringIO)
    def test_parse_error_handling(self, mock_stderr, mock_parse):
        """Test handling of ledger parse errors."""
        mock_parse.side_effect = Exception("Parse error")
        
        with patch('sys.argv', ['verify_citations.py', 'test.md']):
            exit_code = vc.main()
        
        # Default behavior: parse error doesn't fail
        self.assertEqual(exit_code, 0)
    
    @patch('verify_citations.parse_ledger')
    @patch('sys.stderr', new_callable=StringIO)
    def test_parse_error_with_fail_on_error(self, mock_stderr, mock_parse):
        """Test parse error with --fail-on-error."""
        mock_parse.side_effect = Exception("Parse error")
        
        with patch('sys.argv', ['verify_citations.py', 'test.md', '--fail-on-error']):
            exit_code = vc.main()
        
        self.assertEqual(exit_code, 1)


class TestHelperFunctions(unittest.TestCase):
    """Test helper utility functions."""
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        self.assertEqual(vc.normalize_whitespace("  test   quote  here  "), "test quote here")
        self.assertEqual(vc.normalize_whitespace("test\nquote\nhere"), "test quote here")
        self.assertEqual(vc.normalize_whitespace("test\tquote\there"), "test quote here")
        self.assertEqual(vc.normalize_whitespace("test , here"), "test, here")  # Remove space before comma
    
    def test_decode_html_entities(self):
        """Test HTML entity decoding."""
        self.assertEqual(vc.decode_html_entities("test &amp; quote"), "test & quote")
        self.assertEqual(vc.decode_html_entities("test &nbsp; quote"), "test \xa0 quote")
        self.assertEqual(vc.decode_html_entities("test &lt;quote&gt;"), "test <quote>")
    
    def test_extract_text_from_html(self):
        """Test HTML to text extraction."""
        html = "<html><body><p>test quote here</p><script>ignore this</script></body></html>"
        text = vc.extract_text_from_html(html)
        self.assertIn("test quote here", text)
        self.assertNotIn("ignore this", text)

    def test_normalize_latex(self):
        """Test LaTeX normalization."""
        self.assertEqual(vc.normalize_latex("$40\\%$"), "40%")
        self.assertEqual(vc.normalize_latex("$x$"), "x")
        self.assertEqual(vc.normalize_latex("$x+y$"), "x+y")
        self.assertEqual(vc.normalize_latex("\\textbf{test}"), "test")

    def test_strip_quotes(self):
        """Test quote stripping."""
        self.assertEqual(vc.strip_quotes('"test"'), "test")
        self.assertEqual(vc.strip_quotes("'test'"), "test")
        self.assertEqual(vc.strip_quotes("test"), "test")
        self.assertEqual(vc.strip_quotes('"'), '"')  # Single quote character stays

    def test_normalize_unicode_punctuation(self):
        """Test Unicode punctuation normalization."""
        self.assertEqual(vc.normalize_unicode_punctuation("ChatGPT\u2019s"), "ChatGPT's")
        self.assertEqual(vc.normalize_unicode_punctuation('"test"'), '"test"')
        self.assertEqual(vc.normalize_unicode_punctuation('—'), '--')
        self.assertEqual(vc.normalize_unicode_punctuation('–'), '-')

    def test_unicode_quote_matching(self):
        """Test matching with Unicode smart quotes."""
        quote = "ChatGPT's search features"
        # Use actual Unicode right single quotation mark (U+2019)
        content = "OAI-SearchBot is used to surface websites in search results in ChatGPT\u2019s search features."
        self.assertTrue(vc.verify_quote(quote, content))


if __name__ == "__main__":
    unittest.main()
