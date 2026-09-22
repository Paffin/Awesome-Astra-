# Frontend and browser quality

Load for user-visible web UI or frontend behavior. Preserve the repository's design system and
component conventions before adding new primitives.

## Build the complete state machine

Implement the requested journey, not only the ideal screenshot. Cover relevant loading, empty,
success, validation, permission, offline/network, timeout, and recoverable error states. Keep
layout usable with long text, localization, small viewports, zoom, and reduced-motion settings
where they affect the change.

Preserve semantic HTML, keyboard operation, visible focus, accessible names, labels, error
association, contrast, and sensible focus restoration after dialogs or retries. Avoid visual
polish that breaks established tokens or interaction patterns.

## React and rendering

Follow the framework's current project conventions. Avoid unnecessary client state, duplicate
fetches, accidental waterfalls, unstable list identity, and effects that merely synchronize
derivable state. Measure before introducing memoization or caching. Keep server/client
boundaries and serialization contracts explicit.

## Verify as a user

When a browser tool or existing E2E harness is available, exercise the real route and changed
journey: interaction, navigation, validation, error/retry, responsive behavior, and console or
network failures relevant to the task. Do not claim browser verification from a component
snapshot. If no browser is available, run the strongest static/component checks and report the
gap rather than installing automation without need.
