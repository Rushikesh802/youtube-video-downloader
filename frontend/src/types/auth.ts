export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface AuthResponse {
  user?: User;
  token: string;
}
