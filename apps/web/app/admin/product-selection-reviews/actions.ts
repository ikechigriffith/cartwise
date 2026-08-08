'use server';

import { redirect } from 'next/navigation';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const ADMIN_API_TOKEN = process.env.ADMIN_API_TOKEN;

function adminHeaders(): HeadersInit {
  return {
    'content-type': 'application/json',
    ...(ADMIN_API_TOKEN ? { 'x-admin-token': ADMIN_API_TOKEN } : {}),
  };
}

function value(formData: FormData, name: string): string | undefined {
  const item = formData.get(name);
  if (typeof item !== 'string') return undefined;
  const trimmed = item.trim();
  return trimmed.length ? trimmed : undefined;
}

export async function approveProductFamily(selectionKey: string, formData: FormData) {
  const response = await fetch(`${API_BASE_URL}/admin/product-selection-reviews/${encodeURIComponent(selectionKey)}/approve-family`, {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify({
      product_family_id: value(formData, 'product_family_id'),
      notes: value(formData, 'notes'),
    }),
    cache: 'no-store',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API request failed: ${response.status} ${detail}`);
  }
  redirect(`/admin/product-selection-reviews/${encodeURIComponent(selectionKey)}`);
}
