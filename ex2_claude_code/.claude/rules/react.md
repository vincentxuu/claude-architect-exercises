---
paths:
  - "src/components/**/*"
  - "src/pages/**/*"
---

# React Component Conventions

- Use functional components only — no class components
- State management: `useState` for local, `useContext` for shared
- Side effects: always use `useEffect` with explicit dependency arrays
- Name components in PascalCase, hooks in `useCamelCase`
- Extract logic > 10 lines into a custom hook
- Props: define TypeScript interface above the component, not inline
