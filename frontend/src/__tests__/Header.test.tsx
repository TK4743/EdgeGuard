import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Header from '../components/Header';

describe('Header component', () => {
  it('renders company logo slot with expected id and classes', () => {
    const { container } = render(
      <Header
        connected={true}
        statusText="OPERATIONAL"
        statusBg="bg-[#198754] text-white"
        currentTime="14:20:00"
      />
    );

    const logoSlot = container.querySelector('#app-logo-slot');
    expect(logoSlot).toBeInTheDocument();
    expect(logoSlot).toHaveClass('logo-container');
    expect(logoSlot).toHaveAttribute('aria-label', 'Company Logo Slot');
  });

  it('renders title, status text, and current time', () => {
    render(
      <Header
        connected={true}
        statusText="ELEVATED"
        statusBg="bg-[#fd7e14] text-white"
        currentTime="12:34:56"
      />
    );

    expect(screen.getByText(/National Cyber Security Monitoring Centre/i)).toBeInTheDocument();
    expect(screen.getByText('ELEVATED')).toBeInTheDocument();
    expect(screen.getByText('12:34:56')).toBeInTheDocument();
    expect(screen.getByText(/OFFLINE MODE/i)).toBeInTheDocument();
    expect(screen.getByText(/NODE: VE-CAN-01/i)).toBeInTheDocument();
  });
});
