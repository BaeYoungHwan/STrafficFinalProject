package com.aipass;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfigurer implements WebMvcConfigurer {

    private final LoginInterceptor loginInterceptor;

    public WebConfigurer(LoginInterceptor loginInterceptor) {
        this.loginInterceptor = loginInterceptor;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(loginInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/auth/login",
                        "/api/auth/signup",
                        "/api/auth/check-username",
                        "/api/auth/find-id",
                        "/api/auth/find-id-full",
                        "/api/auth/send-code",
                        "/api/auth/verify-code",
                        "/api/auth/verify-reset",
                        "/api/auth/reset-password",
                        "/api/enforcement/webhook",
                        "/api/cctv/ai-target",
                        "/api/sensor/ingest"
                );
    }
}
