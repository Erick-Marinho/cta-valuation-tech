'use client';

import { CircleArrowUp, Mail, Phone } from 'lucide-react';
import { useEffect, useState } from 'react';

// Dados do footer - podem ser importados de um arquivo separado ou de uma API
const footerData = [
	{
		title: 'RECURSOS',
		links: [
			{ text: 'Valoração de Tecnologias', url: '/valoracao' },
			{ text: 'Acesso ao Patrimônio Genético', url: '/patrimonio-genetico' },
			{
				text: 'Conhecimentos Tradicionais',
				url: '/conhecimentos-tradicionais',
			},
			{ text: 'Metodologias de Avaliação', url: '/metodologias' },
			{ text: 'Cálculo de Royalties', url: '/calculo-royalties' },
			{ text: 'Gestão ESG & Compliance', url: '/esg-compliance' },
		],
	},
	{
		title: 'DIMENSÕES DE AVALIAÇÃO',
		links: [
			{ text: 'Contexto Social', url: '/contexto-social' },
			{ text: 'Gestão Ambiental', url: '/gestao-ambiental' },
			{ text: 'Governança', url: '/governanca' },
			{ text: 'Parceria Comercial', url: '/parceria-comercial' },
			{ text: 'Indicadores de Sustentabilidade', url: '/indicadores' },
			{ text: 'Diagnósticos Personalizados', url: '/diagnosticos' },
		],
	},
	{
		title: 'BIODIVERSIDADE',
		links: [
			{ text: 'Convenção sobre Diversidade Biológica', url: '/convencao' },
			{ text: 'Povos e Comunidades Tradicionais', url: '/comunidades' },
			{
				text: 'Exploração Econômica Sustentável',
				url: '/exploracao-sustentavel',
			},
			{ text: 'Repartição de Benefícios', url: '/reparticao-beneficios' },
			{ text: 'Desenvolvimento Comunitário', url: '/desenvolvimento' },
			{ text: 'Impactos Socioambientais', url: '/impactos' },
		],
	},
	{
		title: 'CONTATO',
		links: [
			{ text: 'Sobre Nós', url: '/sobre' },
			{ text: 'Suporte', url: '/suporte' },
			{ text: 'Contato', url: '/contato' },
			{ text: 'Login / Cadastro', url: '/login' },
			{ text: 'Termos e Condições', url: '/termos' },
			{ text: 'Política de Privacidade', url: '/privacidade' },
		],
		contactInfo: [
			{
				icon: Phone,
				text: '+55 79 99169-0222',
				url: 'https://wa.me/5579991690222',
				label: 'WhatsApp',
			},
			{
				icon: Mail,
				text: 'cta.valuation@gmail.com',
				url: 'mailto:cta.valuation@gmail.com',
				label: 'Email',
			},
		],
	},
];

// Componente de coluna do footer
const FooterColumn = ({
	title,
	links,
	contactInfo,
}: {
	title: string;
	links: { text: string; url: string }[];
	contactInfo?: { icon: any; text: string; url: string; label: string }[];
}) => (
	<div className='block grow shrink basis-0 p-3'>
		<h3 className='block tracking-[2px] mb-3.5 font-semibold text-white font-[lexend] leading-6'>
			{title}
		</h3>
		<ul className='block list-none pl-0 m-0 p-0'>
			{links.map((link, index) => (
				<li key={index} className='list-item mb-2.5'>
					<a
						href={link.url}
						className='text-[#8e8e99] hover:text-white transition-colors duration-300 no-underline text-[16px] leading-[24px] font-[lexend]'
					>
						{link.text}
					</a>
				</li>
			))}
		</ul>

		{contactInfo && (
			<div className='mt-6'>
				{contactInfo.map((item, index) => (
					<a
						key={index}
						href={item.url}
						className='flex items-center text-[#8e8e99] hover:text-white transition-colors duration-300 mb-3'
						aria-label={item.label}
					>
						<item.icon size={20} className='mr-2 text-indigo-400' />
						<span className='text-[16px] leading-[24px] font-[lexend]'>
							{item.text}
						</span>
					</a>
				))}
			</div>
		)}
	</div>
);

// Componente principal do footer
export default function Footer() {
	const currentYear = new Date().getFullYear();
	const [showButton, setShowButton] = useState(false);

	const scrollToTop = () => {
		window.scrollTo({
			top: 0,
			behavior: 'smooth',
		});
	};

	useEffect(() => {
		const handleScroll = () => {
			if (window.scrollY > 300) {
				setShowButton(true);
			} else {
				setShowButton(false);
			}
		};

		window.addEventListener('scroll', handleScroll);

		// Limpeza do event listener quando o componente é desmontado
		return () => {
			window.removeEventListener('scroll', handleScroll);
		};
	}, []);

	return (
		<footer className='bg-[#121217] pt-24 pb-12'>
			<div className='container max-w-[1344px] mx-auto px-4'>
				<div className='flex flex-wrap -mx-3'>
					{footerData.map((column, index) => (
						<FooterColumn
							key={index}
							title={column.title}
							links={column.links}
							contactInfo={column.contactInfo}
						/>
					))}
				</div>
				<div className='mt-[100px] w-[48px] mx-auto'>
					<CircleArrowUp
						size={48}
						strokeWidth={1}
						absoluteStrokeWidth
						className='cursor-pointer text-[#8e8e99] hover:text-white transition-colors duration-300'
						onClick={scrollToTop}
						aria-label='Voltar ao topo'
					/>
				</div>

				<div className='mt-12 pt-8 border-t border-gray-800 text-center text-[#8e8e99]'>
					<p className='text-sm'>
						&copy; {currentYear} CTA Value Tech. Todos os direitos reservados.
					</p>
				</div>
			</div>
		</footer>
	);
}
