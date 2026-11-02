import streamlit as st

ABOUT_MD = """
## Bezpieczny system wieloagentowy wspomagający zarządzanie projektami programistycznymi

Aplikacja powstaje w ramach pracy inżynierskiej.

### Cel
Zautomatyzowanie planowania projektu i monitorowania jego postępu, tak aby programista
mógł poświęcić czas na część techniczną, a nie na zarządzanie. Aplikacja jest skierowana do osób
z branży IT, a w szczególności do studentów, którzy realizują projekt w nieznanej im dziedzinie
i potrzebują jasno określonych zadań.

### Jak to działa
1. **Router** wybiera agenta, który ma odpowiedzieć na wiadomość użytkownika.
2. **Interview agent** przeprowadza wywiad i ustala cel, region, termin, technologie, wymagania i styl pracy.
3. **Planner agent** na podstawie wywiadu tworzy plan ogólny (fazy) i szczegółowy (zadania w fazach).
4. **Tracking agent** pobiera commity z GitHuba i na ich podstawie aktualizuje statusy zadań.

### Funkcjonalności
- rozmowa z agentami w jednym oknie czatu,
- automatyczne tworzenie planu projektu z fazami i zadaniami,
- weryfikacja postępu na podstawie commitów i zmian w kodzie (diff),
- podgląd stanu każdego agenta oraz śladu jego działania (wybór agenta, użyte narzędzia).

### Bezpieczeństwo
- uwierzytelnianie użytkowników przez OpenID Connect (konto Google): zaimplementowane,
- każdy agent ma przypisaną własną, ograniczoną listę narzędzi (zasada najmniejszych uprawnień),
- poświadczenia GitHub są czytane ze zmiennych środowiskowych, a nie przechowywane w stanie aplikacji,
- kontrola dostępu RBAC oraz OAuth do narzędzi zewnętrznych: w trakcie realizacji.

### Stos technologiczny
Python, LangGraph / LangChain, Gemini API, Streamlit, GitHub API.

### Ograniczenia
Jedynym źródłem informacji o postępie jest repozytorium GitHub, a jakość statusów zależy od
komunikatów commitów i od modelu językowego. Aplikacja jest prototypem demonstracyjnym.
"""

st.title("About")
st.markdown(ABOUT_MD)