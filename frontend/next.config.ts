import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
	/* config options here */
	env: {
		REACT_APP_API_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
		REACT_APP_THEME: process.env.REACT_APP_THEME || 'light',
		REACT_APP_DEFAULT_LANGUAGE:
			process.env.REACT_APP_DEFAULT_LANGUAGE || 'pt-BR',
		REACT_APP_ENABLE_ANALYTICS:
			process.env.REACT_APP_ENABLE_ANALYTICS || 'false',
		REACT_APP_ENABLE_CHAT_HISTORY:
			process.env.REACT_APP_ENABLE_CHAT_HISTORY || 'true',
		REACT_APP_MAX_DOCS_UPLOAD: process.env.REACT_APP_MAX_DOCS_UPLOAD || '10',
		REACT_APP_CACHE_DURATION: process.env.REACT_APP_CACHE_DURATION || '30',
		REACT_APP_VERSION: process.env.REACT_APP_VERSION || '1.0.0',
	},
	reactStrictMode: true,
	output: 'standalone',
	webpack: (config) => {
		config.watchOptions = {
			poll: 500,
			aggregateTimeout: 200,
			ignored: ['**/node_modules', '**/.git', '**/.next'], // Ignorar diretórios que não precisam ser monitorados
		};
		return config;
	},
};

export default nextConfig;
