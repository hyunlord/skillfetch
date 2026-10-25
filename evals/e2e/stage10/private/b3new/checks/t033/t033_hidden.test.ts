// Hidden objective test for t033 (copied in by check.py, removed afterwards).
import { describe, expect, it } from 'vitest';
import * as mod from '../lib/sanitizeHtml';

type Sanitize = (html: string) => string;
const m = mod as unknown as Record<string, unknown>;
const sanitize = (m.sanitizeHtml ?? m.default) as Sanitize;

function decodeAttr(value: string): string {
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, h: string) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d: string) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

/** All href values of <a> tags in the output, entity-decoded and trimmed. */
function hrefs(html: string): string[] {
  const out: string[] = [];
  const tagRe = /<a\b[^>]*>/gi;
  let tag: RegExpExecArray | null;
  while ((tag = tagRe.exec(html)) !== null) {
    const attr = /\shref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))/i.exec(tag[0]);
    if (attr) out.push(decodeAttr(attr[1] ?? attr[2] ?? attr[3] ?? '').trim());
  }
  return out;
}

const REAL = 'https://example.com/docs?a=1&b=2';
const ENCODED = 'https%3A%2F%2Fexample.com%2Fdocs%3Fa%3D1%26b%3D2';

describe('t033: Google Docs redirect links', () => {
  it('sanitizeHtml is exported', () => {
    expect(typeof sanitize).toBe('function');
  });

  it.each([
    ['https://www.google.com/url?q='],
    ['http://google.com/url?q='],
    ['https://google.com/url?q='],
  ])('unwraps %s wrapper to the real URL', (prefix) => {
    const out = sanitize(`<p>See <a href="${prefix}${ENCODED}&sa=D&source=docs">x</a></p>`);
    expect(hrefs(out)).toEqual([REAL]);
    expect(out).toContain('x');
  });

  it('still drops a wrapped javascript: URL', () => {
    const out = sanitize(
      '<p><a href="https://www.google.com/url?q=javascript%3Aalert(1)&sa=D&source=docs">x</a></p>',
    );
    for (const h of hrefs(out)) {
      const compact = h.replace(/[\s\x00-\x1f]+/g, '');
      expect(compact.toLowerCase()).not.toContain('javascript:');
    }
    expect(out.toLowerCase()).not.toMatch(/href\s*=\s*["']?\s*javascript:/);
  });

  it('leaves a normal link unchanged', () => {
    const out = sanitize('<p>Read <a href="https://example.org/guide#intro">the guide</a>.</p>');
    expect(hrefs(out)).toEqual(['https://example.org/guide#intro']);
  });

  it('does not unwrap non-Google /url?q= links', () => {
    const original = 'https://example.com/url?q=https://evil.test';
    const out = sanitize(`<a href="${original}">y</a>`);
    const found = hrefs(out);
    for (const h of found) {
      expect(h.startsWith('https://evil.test')).toBe(false);
    }
    expect(found).toEqual([original]);
  });

  it('still removes script tags', () => {
    const out = sanitize(
      `<p>a</p><script>alert(1)</script><a href="https://www.google.com/url?q=${ENCODED}&sa=D">x</a>`,
    );
    expect(out.toLowerCase()).not.toContain('<script');
    expect(out).not.toContain('alert(1)');
    expect(hrefs(out)).toEqual([REAL]);
  });
});
