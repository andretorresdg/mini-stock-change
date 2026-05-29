import "@testing-library/jest-dom";

// React Router v7 data router calls `new Request(url, { signal })` during
// client-side navigation. Node.js ≥ 24 undici rejects jsdom's AbortSignal
// because it is not the native class captured at module load time.
// Stripping the signal here keeps navigation working in tests; cancellation
// is not exercised by this suite.
const _Req = globalThis.Request;
class _PatchedRequest extends _Req {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(input, init?.signal != null ? { ...init, signal: undefined } : init);
  }
}
globalThis.Request = _PatchedRequest;
