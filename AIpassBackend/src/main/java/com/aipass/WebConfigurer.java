package com.aipass;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration	// 설정 annotation = 접속허가
public class WebConfigurer implements WebMvcConfigurer{

	@Override
	public void addCorsMappings(CorsRegistry registry) {
		
		// 모든 접속 허용
		registry.addMapping("/**").allowedOrigins("*");
		
		// 3000번 사이트만 허용
		// registry.addMapping("/**").allowedOrigins("http://localhost:3000");
	}
	
}