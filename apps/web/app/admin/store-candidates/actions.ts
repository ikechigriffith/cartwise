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

async function post(path: string, body: unknown) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API request failed: ${response.status} ${detail}`);
  }
}

export async function linkExistingStore(candidateId: string, formData: FormData) {
  await post(`/admin/store-candidates/${candidateId}/link-existing-store`, {
    store_id: value(formData, 'store_id'),
    notes: value(formData, 'notes'),
  });
  redirect(`/admin/store-candidates/${candidateId}`);
}

export async function createStore(candidateId: string, formData: FormData) {
  await post(`/admin/store-candidates/${candidateId}/create-store`, {
    retailer_id: value(formData, 'retailer_id'),
    name: value(formData, 'name'),
    latitude: Number(value(formData, 'latitude')),
    longitude: Number(value(formData, 'longitude')),
    address: { text: value(formData, 'address') ?? '' },
    notes: value(formData, 'notes'),
  });
  redirect(`/admin/store-candidates/${candidateId}`);
}

export async function markRetailerOnly(candidateId: string, formData: FormData) {
  await post(`/admin/store-candidates/${candidateId}/retailer-only`, {
    notes: value(formData, 'notes'),
  });
  redirect(`/admin/store-candidates/${candidateId}`);
}

export async function rejectCandidate(candidateId: string, formData: FormData) {
  await post(`/admin/store-candidates/${candidateId}/reject`, {
    notes: value(formData, 'notes'),
  });
  redirect(`/admin/store-candidates/${candidateId}`);
}
