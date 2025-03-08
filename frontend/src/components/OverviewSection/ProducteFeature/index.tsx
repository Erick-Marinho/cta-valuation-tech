'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useState } from 'react';

export default function ProducteFeature() {
	const [expandido, setExpandido] = useState(false);
	const [selectedTab, setSelectedTab] = useState('diagnosticoSustentavel');

	const backgroundImages = {
		diagnosticoSustentavel: 'carrousel01.jpg',
		calculoRoyalties: 'carrousel02.jpg',
		gestaoEsg: 'teste01.jpg',
		parceriasComerciais: 'carrousel04.jpg',
		impactoSocioambiental: 'carrousel05.jpg',
		reparticaobeneficios: 'carrousel06.jpg',
	};

	type TabValue = keyof typeof backgroundImages;

	const getBackgroundStyle = (tabValue: TabValue) => {
		return {
			backgroundImage: `linear-gradient(
				to bottom,
				#222228 0%,
				#222228 5%,
				rgba(34, 34, 40, 0.8) 25%,
				rgba(34, 34, 40, 0.3) 100%
			), url('/${backgroundImages[tabValue]}')`,
			backgroundPosition: 'center center',
		};
	};
	return (
		<div className='max-w-[1344px]'>
			<Tabs
				defaultValue='diagnosticoSustentavel'
				className='pt-[120px] pb-[60px] ml-auto mr-auto w-full'
				onValueChange={(value) => {
					setSelectedTab(value);
					setExpandido(false);
				}}
			>
				<TabsList
					className={`origin-top flex justify-between w-full p-0 m-0 transition-all duration-800 ease-in-out ${
						expandido ? 'h-[9rem]' : 'h-[6rem]'
					}`}
				>
					<TabsTrigger
						value='diagnosticoSustentavel'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'diagnosticoSustentavel') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'diagnosticoSustentavel') setExpandido(false);
						}}
					>
						Diagnóstico sustentável
					</TabsTrigger>
					<TabsTrigger
						value='calculoRoyalties'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'calculoRoyalties') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'calculoRoyalties') setExpandido(false);
						}}
					>
						Cálculo de royalties
					</TabsTrigger>
					<TabsTrigger
						value='gestaoEsg'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'gestaoEsg') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'gestaoEsg') setExpandido(false);
						}}
					>
						Gestão ESG
					</TabsTrigger>
					<TabsTrigger
						value='parceriasComerciais'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'parceriasComerciais') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'parceriasComerciais') setExpandido(false);
						}}
					>
						Parcerias comerciais
					</TabsTrigger>
					<TabsTrigger
						value='impactoSocioambiental'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'impactoSocioambiental') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'impactoSocioambiental') setExpandido(false);
						}}
					>
						Impacto socioambiental
					</TabsTrigger>
					<TabsTrigger
						value='reparticaobeneficios'
						onClick={() => setExpandido(true)}
						onMouseEnter={() => {
							if (selectedTab === 'reparticaobeneficios') setExpandido(true);
						}}
						onMouseLeave={() => {
							if (selectedTab === 'reparticaobeneficios') setExpandido(false);
						}}
					>
						Repartição de benefícios
					</TabsTrigger>
				</TabsList>
				<TabsContent value='diagnosticoSustentavel'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('diagnosticoSustentavel')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								{/* Mantemos a primeira coluna vazia para preservar o espaço e o posicionamento */}
								<div className='hidden md:block'></div>

								{/* Conteúdo de texto na segunda coluna */}
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Avalie o impacto socioambiental e calcule royalties justos
										para a biodiversidade
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Nosso diagnóstico sustentável analisa 4 dimensões
										essenciais: contexto social, gestão ambiental, governança e
										parcerias comerciais - proporcionando uma visão completa do
										impacto do seu projeto na sociobiodiversidade.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8' />
												<path d='M3 3v5h5' />
												<path d='M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16' />
												<path d='M16 16h5v5' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z' />
												<path d='m22 22-2-2' />
												<path d='M14 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0z' />
												<path d='M10 14a2 2 0 1 1-4 0 2 2 0 0 1 4 0z' />
												<path d='M18 14a2 2 0 1 1-4 0 2 2 0 0 1 4 0z' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M4.9 19.1C1 15.2 1 8.8 4.9 4.9' />
												<path d='M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5' />
												<path d='M14 12a2 2 0 1 0-4 0 2 2 0 0 0 4 0z' />
												<path d='M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5' />
												<path d='M19.1 4.9C23 8.8 23 15.1 19.1 19' />
											</svg>
										</div>
									</div>

									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Iniciar diagnóstico
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
				<TabsContent value='calculoRoyalties'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('calculoRoyalties')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								{/* Mantemos a primeira coluna vazia para preservar o espaço e o posicionamento */}
								<div className='hidden md:block'></div>

								{/* Conteúdo de texto na segunda coluna */}
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Determine valores justos de royalties para recursos da
										biodiversidade
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Nossa ferramenta calcula percentuais monetários destinados à
										repartição de benefícios, considerando diferentes pesos,
										faixas e fatores de correção para garantir compensação
										adequada às comunidades tradicionais e à preservação
										ambiental.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M2 16.1A5 5 0 0 1 5.9 20M2 12.05A9 9 0 0 1 9.95 20M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6' />
												<path d='M2 20h.01' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M3 3v18h18' />
												<path d='m19 9-5 5-4-4-3 3' />
											</svg>
										</div>
									</div>

									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Calcular royalties
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
				<TabsContent value='gestaoEsg'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('gestaoEsg')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								<div className='hidden md:block'></div>
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Fortaleça sua estratégia ESG com biodiversidade e inclusão
										social
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Integre práticas responsáveis de acesso à biodiversidade em
										sua gestão ambiental, social e de governança. Nossa
										ferramenta auxilia no compliance e na demonstração de
										compromisso com a sustentabilidade e as comunidades
										tradicionais.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M22 11.08V12a10 10 0 1 1-5.93-9.14' />
												<path d='m9 11 3 3L22 4' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M12 3c.53 0 1.04.21 1.41.59.38.37.59.88.59 1.41 0 .53-.21 1.04-.59 1.41-.37.38-.88.59-1.41.59-.53 0-1.04-.21-1.41-.59C10.21 6.04 10 5.53 10 5c0-.53.21-1.04.59-1.41C10.96 3.21 11.47 3 12 3z' />
												<path d='M12 14c.53 0 1.04.21 1.41.59.38.37.59.88.59 1.41 0 .53-.21 1.04-.59 1.41-.37.38-.88.59-1.41.59-.53 0-1.04-.21-1.41-.59-.38-.37-.59-.88-.59-1.41 0-.53.21-1.04.59-1.41.37-.38.88-.59 1.41-.59z' />
												<path d='M14 12c0 .53.21 1.04.59 1.41.37.38.88.59 1.41.59.53 0 1.04-.21 1.41-.59.38-.37.59-.88.59-1.41 0-.53-.21-1.04-.59-1.41-.37-.38-.88-.59-1.41-.59-.53 0-1.04.21-1.41.59-.38.37-.59.88-.59 1.41z' />
												<path d='M10 12c0 .53-.21 1.04-.59 1.41-.37.38-.88.59-1.41.59-.53 0-1.04-.21-1.41-.59C6.21 13.04 6 12.53 6 12c0-.53.21-1.04.59-1.41.37-.38.88-.59 1.41-.59.53 0 1.04.21 1.41.59.38.37.59.88.59 1.41z' />
											</svg>
										</div>
									</div>
									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Otimizar estratégia ESG
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
				<TabsContent value='parceriasComerciais'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('parceriasComerciais')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								<div className='hidden md:block'></div>
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Estabeleça parcerias éticas e sustentáveis com comunidades
										tradicionais
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Desenvolva relacionamentos comerciais baseados em equidade e
										respeito mútuo. Nossa ferramenta ajuda a estruturar acordos
										transparentes que valorizam o conhecimento tradicional e
										garantem benefícios justos para todos os envolvidos.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M17 5H7V2h10v3z' />
												<path d='M14 12V8H3v15h4' />
												<path d='M10 8v15' />
												<path d='M21 15v5h-8v-5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2Z' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M16 22h2a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-6.59a1 1 0 0 0-.7.29L8.3 4.7a1 1 0 0 0-.3.71V20a2 2 0 0 0 2 2h2' />
												<path d='M8 13.5V4.1' />
												<path d='M13 19h4' />
												<path d='M13 15h4' />
												<path d='M13 11h4' />
												<path d='M13 7h4' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h1' />
												<path d='M17 3h1a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1' />
												<path d='M12 8v13' />
												<path d='M8 21h8' />
												<path d='M8 6h8' />
											</svg>
										</div>
									</div>
									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Criar parcerias
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
				<TabsContent value='impactoSocioambiental'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('impactoSocioambiental')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								<div className='hidden md:block'></div>
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Monitore e maximize o impacto positivo de seus projetos
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Avalie, quantifique e gerencie os impactos socioambientais
										do acesso à biodiversidade. Nossa ferramenta oferece
										métricas claras e indicadores de sustentabilidade para
										garantir que suas atividades gerem benefícios duradouros
										para as comunidades e o meio ambiente.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M2 12h20' />
												<path d='M12 2v20' />
												<path d='m4.93 4.93 14.14 14.14' />
												<path d='m19.07 4.93-14.14 14.14' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5' />
												<path d='M8.5 8.5v.01' />
												<path d='M16 15.5v.01' />
												<path d='M12 12v.01' />
												<path d='M11 17v.01' />
												<path d='M7 14v.01' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M21 11V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6' />
												<path d='M12 12H3' />
												<path d='M16 6H3' />
												<path d='M12 18H3' />
												<path d='m16 16 5 5' />
												<path d='m21 16-5 5' />
											</svg>
										</div>
									</div>
									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Avaliar impacto
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
				<TabsContent value='reparticaobeneficios'>
					<Card className='border-0 rounded-none'>
						<CardContent
							className='custom-card-bg relative py-16 px-8 bg-[#222228] text-white min-h-[500px]'
							style={getBackgroundStyle('reparticaobeneficios')}
						>
							<div className='grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto'>
								<div className='hidden md:block'></div>
								<div className='flex flex-col justify-center space-y-6 animate-[fadeRight_1.2s_cubic-bezier(0.25,0.1,0.25,1)_0.2s_forwards] opacity-0 will-change-[transform,opacity]'>
									<h2 className='text-4xl md:text-5xl font-bold leading-tight'>
										Distribua os benefícios de forma equitativa e transparente
									</h2>
									<p className='text-lg opacity-90 max-w-xl'>
										Atenda aos princípios da Convenção sobre Diversidade
										Biológica com um sistema justo de repartição de benefícios.
										Nossa ferramenta determina percentuais adequados e estrutura
										acordos que valorizam o conhecimento tradicional e promovem
										o desenvolvimento comunitário.
									</p>
									<div className='flex items-center space-x-6 pt-4'>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M20 16V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v9m16 0H4m16 0 1.28 2.55a1 1 0 0 1-.9 1.45H3.62a1 1 0 0 1-.9-1.45L4 16' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<circle cx='12' cy='12' r='10' />
												<path d='m15 9-6 6' />
												<path d='m9 9 6 6' />
											</svg>
										</div>
										<div className='bg-amber-50 h-12 w-12 rounded-full flex items-center justify-center'>
											<svg
												xmlns='http://www.w3.org/2000/svg'
												width='24'
												height='24'
												viewBox='0 0 24 24'
												fill='none'
												stroke='#222228'
												strokeWidth='2'
												strokeLinecap='round'
												strokeLinejoin='round'
											>
												<path d='M21 10V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l2-1.14' />
												<path d='M16.5 9.4 7.55 4.24' />
												<path d='M12 12v10' />
												<path d='M3.29 7 12 12l8.71-5' />
												<circle cx='18.5' cy='15.5' r='2.5' />
												<path d='M20.27 17.27 22 19' />
											</svg>
										</div>
									</div>
									<div className='pt-8'>
										<button className='bg-transparent hover:bg-amber-50 text-white hover:text-[#222228] border-2 border-white hover:border-amber-50 font-medium py-3 px-8 rounded-md transition duration-300'>
											Estruturar repartição
										</button>
									</div>
								</div>
							</div>
						</CardContent>
					</Card>
				</TabsContent>
			</Tabs>
		</div>
	);
}
