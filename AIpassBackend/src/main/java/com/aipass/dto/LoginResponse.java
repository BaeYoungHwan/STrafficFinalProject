package com.aipass.dto;

public class LoginResponse {
    private String username;
    private String name;

    public LoginResponse(String username, String name) {
        this.username = username;
        this.name = name;
    }

    public String getUsername() { return username; }
    public String getName() { return name; }
}
