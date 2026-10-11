const StateContainer = ({ icon, iconVariant = 'muted', title, message, children }) => {
  return (
    <div className="state-container fade-in">
      {icon && <div className={`state-icon ${iconVariant}`}>{icon}</div>}
      <div className="state-title">{title}</div>
      {message && <div className="state-message">{message}</div>}
      {children}
    </div>
  )
}

export const LoadingState = ({ message = 'Loading…', label = '' }) => (
  <StateContainer
    icon={<div className="spinner-border spinner-border-sm" role="status" />}
    iconVariant="powder"
    title={message}
    message={label}
  />
)

export const EmptyState = ({ icon, title = 'Nothing here yet', message, children }) => (
  <StateContainer icon={icon} iconVariant="muted" title={title} message={message}>
    {children}
  </StateContainer>
)

export const ErrorState = ({ title = 'Something went wrong', message, children }) => (
  <StateContainer
    icon='!'
    iconVariant="peach"
    title={title}
    message={message}
  >
    {children}
  </StateContainer>
)

export const UnavailableState = ({ title = 'Backend connection unavailable', message, children }) => (
  <StateContainer
    icon='—'
    iconVariant="yellow"
    title={title}
    message={message}
  >
    {children}
  </StateContainer>
)

export default StateContainer
