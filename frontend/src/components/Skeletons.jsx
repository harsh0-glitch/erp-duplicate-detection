export const TableSkeleton = ({ rows = 5, cols = 6 }) => (
  <div style={{ padding: 'var(--space-4)' }}>
    {Array.from({ length: rows }).map((_, r) => (
      <div
        key={r}
        style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {Array.from({ length: cols }).map((_, c) => (
          <div
            key={c}
            className="skeleton skeleton-line"
            style={{ flex: 1, height: '14px' }}
          />
        ))}
      </div>
    ))}
  </div>
)

export const CardSkeleton = () => (
  <div style={{ padding: 'var(--space-4)' }}>
    <div className="skeleton skeleton-line medium" style={{ height: '20px', marginBottom: '12px' }} />
    <div className="skeleton skeleton-line" />
    <div className="skeleton skeleton-line short" />
  </div>
)

export const StatSkeleton = () => (
  <div>
    <div className="skeleton skeleton-line short" style={{ height: '10px', marginBottom: '8px' }} />
    <div className="skeleton" style={{ height: '24px', width: '45%' }} />
  </div>
)

export default TableSkeleton
