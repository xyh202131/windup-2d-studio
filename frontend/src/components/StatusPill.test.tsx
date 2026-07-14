import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusPill } from './StatusPill'

describe('StatusPill', () => {
  it('renders a localized review status', () => {
    render(<StatusPill status="awaiting_review" />)
    expect(screen.getByText('等待审核')).toBeInTheDocument()
  })
})

