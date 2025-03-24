'use client';

import { config } from '@/lib/config';

/**
 * Componente que exibe informações de configuração do sistema
 */
const ConfigInfo = () => {
	return (
		<div className='p-4 bg-slate-50 rounded-lg shadow-sm'>
			<h2 className='text-lg font-semibold mb-3 text-slate-800'>
				Informações do Sistema
			</h2>
			<div className='space-y-2'>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Versão:</span>
					<span className='text-slate-700'>{config.appVersion}</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>API:</span>
					<span className='text-slate-700'>{config.apiUrl}</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Tema:</span>
					<span className='text-slate-700'>{config.theme}</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Idioma:</span>
					<span className='text-slate-700'>{config.defaultLanguage}</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Ambiente:</span>
					<span
						className={`${
							config.nodeEnv === 'development'
								? 'text-amber-600'
								: 'text-green-600'
						}`}
					>
						{config.nodeEnv}
					</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Histórico de chat:</span>
					<span
						className={`${
							config.enableChatHistory ? 'text-green-600' : 'text-red-600'
						}`}
					>
						{config.enableChatHistory ? 'Ativado' : 'Desativado'}
					</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Analytics:</span>
					<span
						className={`${
							config.enableAnalytics ? 'text-green-600' : 'text-red-600'
						}`}
					>
						{config.enableAnalytics ? 'Ativado' : 'Desativado'}
					</span>
				</p>
				<p className='flex justify-between border-b border-slate-200 pb-1'>
					<span className='font-medium text-slate-600'>Máx. documentos:</span>
					<span className='text-slate-700'>{config.maxDocsUpload}</span>
				</p>
				<p className='flex justify-between'>
					<span className='font-medium text-slate-600'>Cache (min):</span>
					<span className='text-slate-700'>{config.cacheDuration}</span>
				</p>
			</div>
		</div>
	);
};

export default ConfigInfo;
