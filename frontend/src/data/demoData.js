/**
 * PREVIEW DATA — clearly labeled.
 * Used only for visual development when the backend is unavailable.
 * Remove this file or stop importing it once the backend is connected.
 */

export const previewProducts = [
  {
    id: 'p-001',
    sku: 'LP-Dell-XPS15-2024',
    name: 'Dell XPS 15 9530',
    description: '15.6-inch premium ultrabook with OLED display',
    brand: 'Dell',
    category: 'Laptops',
    subcategory: 'Ultrabooks',
    unit: 'pcs',
    is_active: true,
    attributes: {
      Processor: 'Intel Core i7-13700H',
      RAM: '16 GB',
      Storage: '1 TB SSD',
      'Screen Size': '15.6 inch',
      Color: 'Platinum Silver',
    },
    created_at: '2025-09-12T10:30:00Z',
    updated_at: '2025-09-28T14:20:00Z',
  },
  {
    id: 'p-002',
    sku: 'LP-Dell-XPS15-9530',
    name: 'Dell XPS 15 9530 OLED',
    description: '15.6-inch ultrabook, OLED variant',
    brand: 'Dell',
    category: 'Laptops',
    subcategory: 'Ultrabooks',
    unit: 'pcs',
    is_active: true,
    attributes: {
      Processor: 'Intel Core i7-13700H',
      RAM: '16 GB',
      Storage: '1 TB SSD',
      'Screen Size': '15.6 inch',
      Color: 'Graphite',
    },
    created_at: '2025-09-15T09:00:00Z',
    updated_at: '2025-09-15T09:00:00Z',
  },
  {
    id: 'p-003',
    sku: 'GP-NV-RTX4060-8G',
    name: 'NVIDIA GeForce RTX 4060 8GB',
    description: 'Mid-range gaming GPU',
    brand: 'NVIDIA',
    category: 'GPUs',
    subcategory: 'Desktop Graphics Cards',
    unit: 'pcs',
    is_active: true,
    attributes: {
      Memory: '8 GB GDDR6',
      'Boost Clock': '2460 MHz',
      'Power Connector': '8-pin',
      Color: 'Black',
    },
    created_at: '2025-08-20T12:00:00Z',
    updated_at: '2025-08-20T12:00:00Z',
  },
]

export const previewDuplicates = [
  {
    id: 'd-001',
    product_a: previewProducts[0],
    product_b: previewProducts[1],
    status: 'pending',
    confidence: null,
    rank: 1,
    matching_features: ['brand', 'category', 'processor', 'ram', 'storage', 'screen_size'],
    created_at: '2025-09-16T08:00:00Z',
    review_status: 'pending',
    reviewer: null,
    reason: null,
    reviewed_at: null,
  },
]

export const previewReviews = [
  {
    id: 'd-001',
    product_name: 'Dell XPS 15 9530',
    candidate_name: 'Dell XPS 15 9530 OLED',
    status: 'pending',
    reviewer: null,
    reason: null,
    reviewed_at: null,
  },
]
