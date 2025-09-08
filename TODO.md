# TODO
## Checklist
- [ ] Untangle memory
- [ ] Untangle history
- [ ] Untangle all components that rely on state
- [ ] Accounts
- [ ] Saving chats
- [ ] MongoDB hosting
## Suggestions

1. Dependency Injection: — Investigated
- The MedicalHistoryManager could use a more formal DI pattern
- Consider using FastAPI's dependency injection more extensively

2. Configuration Management: — Half done
- Magic numbers and constants should be moved to a central config file
- Environment variables should be validated at startup

3. Error Handling:
- Need more specific exception types instead of generic Exception
- Should have consistent error handling patterns across modules

4. Service Layer Separation:
- Business logic in MedicalHistoryManager could be split into separate services
- Summary generation could be its own service class

5. Interface Definitions:
- Missing clear interface definitions for major components
- Should define abstract base classes for key services

6. Testing Structure:
- No clear separation of unit vs integration tests
- Missing test fixtures and mocks

7. Logging Strategy: — Done
- Inconsistent logging levels across components
- Missing structured logging format definition

8. Type Hints:
- Some function parameters missing type hints
- Return types could be more specific using TypeVar

9. Documentation:
- Missing detailed API documentation
- Inconsistent docstring formats

10. State Management:
- Global state in MedicalState could be improved
- Session management could be more robust
