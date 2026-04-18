import { afterEach, describe, expect, it, vi } from 'vitest'

import { PreviewData } from '../types'
import { loadPdf, PDF_PREVIEW_SIZE } from './Pdf'

vi.mock('constants/config', () => ({
  default: {
    apiGatewayEndpoint: 'https://catalog.example',
  },
}))

describe('components/Preview/loaders/Pdf', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests the larger preview size and page count for PDFs', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(new Blob(['page-1']), {
          status: 200,
          headers: {
            'X-Quilt-Info': JSON.stringify({ page_count: 25 }),
          },
        }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const sign = vi.fn(() => 'https://signed.example/sample.pdf')
    const handle = { key: 'docs/sample.pdf' }

    const result = await loadPdf({ sign, handle })

    expect(sign).toHaveBeenCalledWith(handle)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const requestUrl = new URL(fetchMock.mock.calls[0][0])
    expect(requestUrl.pathname).toBe('/thumbnail')
    expect(requestUrl.searchParams.get('url')).toBe('https://signed.example/sample.pdf')
    expect(requestUrl.searchParams.get('input')).toBe('pdf')
    expect(requestUrl.searchParams.get('size')).toBe(PDF_PREVIEW_SIZE)
    expect(requestUrl.searchParams.get('countPages')).toBe('true')

    expect(PreviewData.Pdf.is(result)).toBe(true)
    expect(PreviewData.Pdf.unbox(result)).toMatchObject({
      handle,
      pages: 25,
      type: 'pdf',
    })
    expect(PreviewData.Pdf.unbox(result).firstPageBlob.size).toBe(6)
  })

  it('detects pptx previews and uses the same larger size', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(new Blob(['slide-1']), {
          status: 200,
          headers: {
            'X-Quilt-Info': JSON.stringify({ page_count: 5 }),
          },
        }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const handle = { logicalKey: 'slides/Deck.PPTX', key: 'slides/deck.pptx' }

    const result = await loadPdf({
      sign: () => 'https://signed.example/deck.pptx',
      handle,
    })

    const requestUrl = new URL(fetchMock.mock.calls[0][0])
    expect(requestUrl.searchParams.get('input')).toBe('pptx')
    expect(requestUrl.searchParams.get('size')).toBe(PDF_PREVIEW_SIZE)
    expect(PreviewData.Pdf.is(result)).toBe(true)
    expect(PreviewData.Pdf.unbox(result)).toMatchObject({
      handle,
      pages: 5,
      type: 'pptx',
    })
  })
})
