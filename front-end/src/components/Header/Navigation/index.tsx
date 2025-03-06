import { NavigationMenuDemo } from '@/components/NavigationMenu';
import Image from 'next/image';

export default function Navigation() {
	return (
		<header className='absolute w-full mt-[60px] text-[14px] font-normal text-[#fff] z-10'>
			<nav className='relative flex !p-0 items-stretch w-[1344px] max-w-[1344px] m-auto max-h-12'>
				<a
					href='#'
					className='flex overflow-hidden pr-[25px] border-r border-white/30 animate-navItemFade border-0 flex-nowrap whitespace-nowrap items-center cursor-pointer no-underline'
				>
					<Image src='/logo_2.png' alt='Logo' width={120} height={120} />
					<div className='animate-[fadeRight_3s_ease-out_forwards] mr-2'>
						CTA VALUATION TECH
					</div>
					<div></div>
				</a>
				<NavigationMenuDemo />
			</nav>
		</header>
	);
}
