import { afterEach, describe, expect, it, vi } from 'vitest'

import { loadBlob, PDF_PREVIEW_SIZE } from './Pdf'

vi.mock('constants/config', () => ({
  default: {
    apiGatewayEndpoint: 'https://catalog.example',
  },
}))

describe('components/Preview/renderers/Pdf', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reuses the first page blob without refetching', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const firstPageBlob = new Blob(['page-1'])

    const result = await loadBlob({
      sign: vi.fn(),
      handle: { key: 'docs/sample.pdf' },
      page: 1,
      firstPageBlob,
      type: 'pdf',
    })

    expect(result).toBe(firstPageBlob)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('requests the larger preview size for subsequent pages', async () => {
    const nextPageBlob = new Blob(['page-2'])
    const fetchMock = vi.fn(async () => new Response(nextPageBlob, { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const sign = vi.fn(() => 'https://signed.example/sample.pdf')
    const handle = { key: 'docs/sample.pdf' }

    const result = await loadBlob({
      sign,
      handle,
      page: 2,
      firstPageBlob: new Blob(['page-1']),
      type: 'pdf',
    })

    expect(sign).toHaveBeenCalledWith(handle)
    expect(result.size).toBe(nextPageBlob.size)

    const requestUrl = new URL(fetchMock.mock.calls[0][0])
    expect(requestUrl.pathname).toBe('/thumbnail')
    expect(requestUrl.searchParams.get('url')).toBe('https://signed.example/sample.pdf')
    expect(requestUrl.searchParams.get('input')).toBe('pdf')
    expect(requestUrl.searchParams.get('size')).toBe(PDF_PREVIEW_SIZE)
    expect(requestUrl.searchParams.get('page')).toBe('2')
  })

  it('passes through the requested page for later navigation', async () => {
    const fetchMock = vi.fn(
      async () => new Response(new Blob(['page-25']), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await loadBlob({
      sign: () => 'https://signed.example/sample.pdf',
      handle: { key: 'docs/sample.pdf' },
      page: 25,
      firstPageBlob: new Blob(['page-1']),
      type: 'pdf',
    })

    const requestUrl = new URL(fetchMock.mock.calls[0][0])
    expect(requestUrl.searchParams.get('page')).toBe('25')
    expect(requestUrl.searchParams.get('size')).toBe(PDF_PREVIEW_SIZE)
  })
})
