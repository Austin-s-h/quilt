import * as React from 'react'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { ThemeProvider, createMuiTheme } from '@material-ui/core/styles'
import { afterEach, describe, expect, it, vi } from 'vitest'

import JsonDisplay from './JsonDisplay'

vi.mock('use-resize-observer', () => ({
  default: () => ({ width: 480 }),
}))

const theme = createMuiTheme()
;(theme.typography as any).monospace = {
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

  it('allows collapsed rows to wrap within the container', async () => {
    renderWithTheme(
      <JsonDisplay
        defaultExpanded={0}
        name="Metadata"
        value={{
          beginanalysis: '1',
          begindata: '2',
          beginstext: '3',
          byteord: '1,2,3,4',
          datatype: 'F',
          endanalysis: '4',
          enddata: '5',
          endstext: '6',
          veryLongKeyNameThatWouldOtherwiseForceTheCollapsedRowToStayOnOneLine:
            'abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz',
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/Metadata:/i)).toBeTruthy()
    })

    const row = screen.getByText(/Metadata:/i).parentElement
    expect(row).toBeTruthy()
    expect(window.getComputedStyle(row as Element).display).toBe('flex')
    expect(window.getComputedStyle(row as Element).flexWrap).toBe('wrap')
  })

  it('can collapse objects to a compact summary without listing keys', async () => {
    renderWithTheme(
      <JsonDisplay
        defaultExpanded={0}
        name="Metadata"
        showKeysWhenCollapsed={false}
        value={{
          beginanalysis: '1',
          begindata: '2',
          beginstext: '3',
          byteord: '1,2,3,4',
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText(/Metadata:/i)).toBeTruthy()
    })

    const row = screen.getByText(/Metadata:/i).parentElement
    expect(row?.textContent).toContain('<…4>')
    expect(row?.textContent).not.toContain('beginanalysis')
  })

  it('resets compound expansion when the value changes', async () => {
    const { rerender } = renderWithTheme(
      <JsonDisplay defaultExpanded={1} name="Metadata" value={{ beginanalysis: '1' }} />,
    )

    await screen.findByText(/beginanalysis:/i)
    fireEvent.click(screen.getByText(/Metadata:/i).parentElement as Element)

    rerender(
      <ThemeProvider theme={theme}>
        <JsonDisplay defaultExpanded={1} name="Metadata" value={{ endanalysis: '2' }} />
      </ThemeProvider>,
    )

    await screen.findByText(/endanalysis:/i)
    expect(screen.queryByText(/beginanalysis:/i)).toBeNull()
  })
})
