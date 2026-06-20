import * as React from 'react'
import { render, screen, cleanup } from '@testing-library/react'
import { ThemeProvider, createMuiTheme } from '@material-ui/core/styles'
import { afterEach, describe, expect, it, vi } from 'vitest'

import JsonDisplay from './JsonDisplay'

vi.mock('use-resize-observer', () => ({
  default: () => ({ width: 480 }),
}))

const theme = createMuiTheme()
;(
  theme.typography as typeof theme.typography & { monospace: { fontFamily: string } }
).monospace = {
  fontFamily: 'monospace',
}

function renderWithTheme(component: React.ReactElement) {
  return render(<ThemeProvider theme={theme}>{component}</ThemeProvider>)
}

describe('components/JsonDisplay', () => {
  afterEach(cleanup)

  it('wraps long metadata values without forcing horizontal overflow', async () => {
    const { container } = renderWithTheme(
      <JsonDisplay
        defaultExpanded={1}
        value={{
          longField:
            'Event,Time,FSC-A,SSC-A,BL1-A,BL2-A,BL3-A,VL1-A,VL2-A,VL3-A,FSC-H,SSC-H,BL1-H,BL2-H,BL3-H,VL1-H,VL2-H,VL3-H,FSC-W,SSC-W,BL1-W,BL2-W,BL3-W,VL1-W,VL2-W,VL3-W',
        }}
      />,
    )

    await screen.findByText(/Event,Time,FSC-A,SSC-A/)
    const root = container.firstElementChild

    expect(root).toBeTruthy()
    expect(window.getComputedStyle(root as Element).whiteSpace).toBe('pre-wrap')
    expect(window.getComputedStyle(root as Element).overflowWrap).toBe('anywhere')
    expect(window.getComputedStyle(root as Element).wordBreak).toBe('break-word')
  })
})
