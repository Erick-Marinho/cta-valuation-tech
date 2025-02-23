import { NavigationMenuDemo } from '@/components/NavigationMenu';
import { ModeToggle } from '@/components/ui/ModeToogle';

export default function Home() {
	return (
		<div className='flex justify-center items-start mt-[60px] h-screen'>
			<div className='flex'>
				<NavigationMenuDemo />
				<ModeToggle />
			</div>
		</div>
	);
}
