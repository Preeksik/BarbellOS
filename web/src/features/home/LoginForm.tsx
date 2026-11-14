import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { type Session, api } from "../../lib/api";

export function LoginForm() {
  const [password, setPassword] = useState("");
  const client = useQueryClient();
  const login = useMutation({
    mutationFn: () => api.post<Session>("/api/auth/login", { password }),
    retry: false,
    onSuccess: (session) => client.setQueryData(["me"], session),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate();
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>Logowanie</h2>
      <label>
        Hasło
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <button type="submit" className="primary" disabled={!password || login.isPending}>
        Zaloguj
      </button>
      {login.error && <p className="error">{login.error.message}</p>}
    </form>
  );
}
