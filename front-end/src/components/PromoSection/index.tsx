import PromoContainer from './PromoContainer';
import PromoService from './PromoService';
export default function PromoSection() {
	return (
		<div className='bg-[#fff] text-[#303030] block items-stretch'>
			<PromoContainer />
			<PromoService />
		</div>
	);
}
