'use client';

import { Menu } from 'lucide-react';
import Image from 'next/image';
import { NavigationMenuDemo } from '../NavigationMenu';
import { ModeToggle } from '../ui/ModeToogle';

export default function Header() {
	return (
		<div className='absolute top-0 w-full z-10'>
			<div className='hidden md:flex justify-center items-center mt-[60px] w-full px-4 relative max-w-fit ml-auto mr-auto'>
				<div className='left-4'>
					<Image src='/logo_2.png' alt='Logo' width={120} height={120} />
				</div>
				<div className='flex flex-col items-center'>
					<h1 className='animate-[fadeRight_3s_ease-out_forwards] mr-2 text-[16px] font-[lexend]'>
						CTA VALUATION TECH
					</h1>
				</div>
				<div className='flex justify-center items-center mx-auto ml-2 mr-2 border-l-1 border-r-1 border-solid border-zinc-600 h-10 font-[lexend] text-[14px]'>
					<NavigationMenuDemo />
				</div>
				<div className='pl-2'>
					<ModeToggle />
				</div>
			</div>

			<div className='flex md:hidden items-center mt-[60px] w-full px-4'>
				<div>
					<Image src='/logo_2.png' alt='Logo' width={100} height={100} />
				</div>
				<div className='ml-auto'>
					<Menu />
				</div>
			</div>
		</div>
	);
}
