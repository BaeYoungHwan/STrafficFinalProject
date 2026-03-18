package com.aipass.dto;

public class LoginResponse {
    private String username;
    private String name;
    private String role;

    public LoginResponse(String username, String name, String role) {
        this.username = username;
        this.name = name;
        this.role = role;
    }

    public String getUsername() { return username; }
    public String getName() { return name; }
    public String getRole() { return role; }
}
