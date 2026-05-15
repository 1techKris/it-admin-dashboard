import { useState } from "react";
import api from "../../lib/api/client";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await api.post("/auth/login", { username, password });
      localStorage.setItem("token", res.data.access_token);
      window.location.href = "/";
    } catch {
      setError("Invalid username or password");
    }
  }

  return (
    <form onSubmit={submit} className="max-w-sm mx-auto mt-24">
      <h1 className="text-xl mb-4">Sign in</h1>
      {error && <div className="text-red-600">{error}</div>}
      <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" />
      <button type="submit">Login</button>
    </form>
  );
}