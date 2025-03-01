import Header from '@/components/Header';
import HeroSection from '@/components/HeroSection';
import OverviewSection from '@/components/OverviewSection';

export default function Home() {
	return (
		<div className='relative'>
			<Header />
			<HeroSection />
			<OverviewSection />
		</div>
	);
}
