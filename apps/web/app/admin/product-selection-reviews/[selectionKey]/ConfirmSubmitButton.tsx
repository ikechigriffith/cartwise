'use client';

import type { ReactNode } from 'react';

export function ConfirmSubmitButton({ children, message }: { children: ReactNode; message: string }) {
  return <button type="submit" onClick={(event) => { if (!window.confirm(message)) event.preventDefault(); }}>{children}</button>;
}
