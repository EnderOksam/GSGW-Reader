export function parseScopes(raw: string | null | undefined): string[] {
  return (raw ?? "")
    .split(/[,\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function hasRepoScope(raw: string | null | undefined): boolean {
  const scopes = parseScopes(raw);
  return scopes.includes("repo") || scopes.includes("public_repo");
}
