'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useState } from 'react';

export default function OverviewSection() {
	const [expandido, setExpandido] = useState(false);
	const [selectedTab, setSelectedTab] = useState('diagnosticoSustentavel');

	return (
		<section className='bg-amber-50'>
			<div className='relative m-auto max-w-7xl'>
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
								if (selectedTab === 'diagnosticoSustentavel')
									setExpandido(true);
							}}
							onMouseLeave={() => {
								if (selectedTab === 'diagnosticoSustentavel')
									setExpandido(false);
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
								if (selectedTab === 'impactoSocioambiental')
									setExpandido(false);
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
						<Card className=''>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
					<TabsContent value='calculoRoyalties'>
						<Card>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
					<TabsContent value='gestaoEsg'>
						<Card>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
					<TabsContent value='parceriasComerciais'>
						<Card>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
					<TabsContent value='impactoSocioambiental'>
						<Card>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
					<TabsContent value='reparticaobeneficios'>
						<Card>
							<CardContent className='custom-card-bg'></CardContent>
						</Card>
					</TabsContent>
				</Tabs>
			</div>
		</section>
	);
}
