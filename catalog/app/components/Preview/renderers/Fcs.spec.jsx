import * as React from 'react'
import { render, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import Fcs from './Fcs'

vi.mock('./Vega', () => ({
  default: ({ spec }) => <div data-testid="fcs-vega">{spec.title.text}</div>,
}))

describe('components/Preview/renderers/Fcs', () => {
  afterEach(cleanup)

  it('renders the vega-lite scatter plot when provided', () => {
    const { getByTestId, container } = render(
      <Fcs
        metadata={{ specimen: 'demo' }}
        preview="<div><table class='dataframe'><tbody><tr><td>1</td></tr></tbody></table></div>"
        vegaLite={{ title: { text: 'FSC-A vs SSC-A' } }}
      />,
    )

    expect(getByTestId('fcs-vega').textContent).toBe('FSC-A vs SSC-A')
    expect(container.querySelector('table.dataframe')).toBeTruthy()
  })
})
