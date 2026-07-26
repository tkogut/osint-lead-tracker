---
name: accint-solve
description: Route a goal through acc's scored-memory loop via acc_act(runtime="solve"); deliberate any returned brain_frame and submit via continue.
---

# 🧠 accint-solve

🎯 **Purpose**
Prowadzenie wnioskowania (resolving) i rozwiązywanie skomplikowanych problemów w pętli pamięci rozproszonej za pomocą narzędzi serwera MCP `accreted-intelligence`.

🛠️ **Logic & Workflow**

1. **Uruchomienie (Start)**:
   Wywołaj narzędzie MCP:
   `acc_act(runtime="solve", input="<Twój cel / opis zagadnienia>")`

2. **Obsługa Wyniku (Handling results)**:
   - **Stan Końcowy (Final outcome)**: Jeżeli rezultat jest ostateczny, wyświetl użytkownikowi gotowe rozwiązanie, identyfikator zobowiązania (`commitment id`) oraz powiązane cytowania `[ids]`.
   - **Stan Klatki Myślowej (Brain Frame)**: Jeżeli serwer zwróci klatkę myślową (`brain_frame`), przeanalizuj brakujące dane (holes), pobrane informacje oraz predykcje, a następnie wyślij kolejny krok wnioskowania przy użyciu:
     `acc_act(runtime="continue", input="<kolejny krok analizy>")`

3. **Zasada Pętli (Feedback Loop)**:
   Powtarzaj krok 2 aż do uzyskania stanu końcowego (Evidence-based closure).
