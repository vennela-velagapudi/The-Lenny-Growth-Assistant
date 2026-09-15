// @vitest-environment jsdom
import { expect, test } from 'vitest';
import DOMPurify from 'dompurify';

test('HTML artifact is sanitized by DOMPurify', () => {
  const maliciousHTML = '<div onclick="alert(\'XSS\')">Test</div><script>localStorage.getItem("token")</script>';
  const sanitized = DOMPurify.sanitize(maliciousHTML);
  expect(sanitized).not.toContain('<script>');
  expect(sanitized).not.toContain('onclick');
  expect(sanitized).toContain('<div>Test</div>');
});
