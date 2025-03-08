import Footer from '@/components/Footer';
import Header from '@/components/Header';
import HeroSection from '@/components/HeroSection';
import OverviewSection from '@/components/OverviewSection';
import PromoSection from '@/components/PromoSection';
import VideoPromo from '@/components/VideoPromo';

export default function Home() {
	return (
		<div className='relative'>
			<Header />
			<HeroSection />
			<OverviewSection />
			<VideoPromo />
			<PromoSection />
			<Footer />
		</div>
	);
}
