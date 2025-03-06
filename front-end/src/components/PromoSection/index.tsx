import PromoContainer from './PromoContainer';
import PromoService from './PromoService';
export default function PromoSection() {
	return (
		<section className='bg-[#FFFCF5] text-[#303030] p-0 block items-stretch'>
			<PromoContainer />
			<PromoService />
		</section>
	);
}
