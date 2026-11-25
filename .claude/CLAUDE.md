**ARCHITECTURE**
docs/
├── changelogs/
|
src/
├── app/                      # Root shell
│   ├── presentation/         # Root layout, navigation, theme provider
│   ├── di/                   # Global DI container — eager, app boot
│   ├── config/               # Env vars, feature flags, constants (never inline)
│   └── utils/                # App-wide helpers owned by no feature
│
├── shared/
│   ├── kernel/               # ONLY freely-importable layer
│   │   ├── types/            # Branded IDs, Result/Either, base Failure
│   │   └── contracts/        # IUseCase, IRepository, ITool, IAgent
│   ├── ui/                   # Design system + tokens
│   ├── infrastructure/       # Pure infra, zero domain logic
│   │   ├── http/             # Client, interceptors, base config
│   │   ├── storage/          # Local/secure storage, cache wrappers
│   │   ├── logger/           # Structured logging adapter
│   │   └── analytics/        # Event tracking adapter (SDK-agnostic)
│   └── utils/                # Formatters, validators, shared hooks
│
├── agents/                   # ⚠️ OPTIONAL — only if the product itself ships AI features
│   ├── orchestrator/         # planner.ts (goal → steps), router.ts (step → agent)
│   ├── memory/               # Tiered stores per the memory taxonomy: episodic · semantic · procedural · prospective
│   ├── tools/[tool]/         # definition.ts (schema model sees) · executor.ts (validates, calls use cases)
│   ├── prompts/              # Versioned system prompts & templates
│   ├── evals/                # Golden datasets + regression evals per agent
│   ├── middleware/           # output-validator · safety-guard · rate-limiter · tracer
│   └── [agent-name]/         # agent.ts (role, model, tool subset) · workflows/
│
└── features/[feature]/
    ├── domain/               # Pure logic, zero framework/infra imports
    │   ├── entities/
    |    ├── repositories/ (interfaces only)  └── usecases/ (one class per action)
    ├── data/
    │   ├── datasources/remote/ + local/   # speak DTOs only
    │   ├── models/ (DTOs)
    |   ├── mappers/ (DTO ↔ Entity)
    |   └── repositories/ (implementations)
    ├── presentation/
    │   ├── pages/ (thin)
    |   ├── components/
    |   └── viewmodels/ (all UI logic/state)
    ├── agents/               # OPTIONAL — feature-scoped tools/ + workflows/
    └── di/                   # Feature-scoped injector, lazy on route entry
```

**Other Constraints**
- lines per file must be optimal at 200 but maximum lines is 250
- Always commit and edit changelogs (if it doesn't create a /docs folder and add a CHANGELOGS.md)

**ALWAYS USE**
- /vibe-wise:learn 
- /superpowers:using-superpowers  — find relevant skills
- /ponytail
- /apple-design and /design-taste-frontend — Judge and critic the UI
- /code-reviewer for Judge and critic the code quality too 
- /cloudflare-security-audit for security 

**USE WHEN WE HAVE REPO REFERENCES**
- /reverse-engineer-anything
