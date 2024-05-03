import NavBar from "./NavBar";
import { Outlet, useNavigation } from "react-router-dom";

const RootLayout = () => {
    const navigation = useNavigation();
    return (
        <>
            {navigation.state === 'loading' && <p>Loading...</p>}
            <NavBar />
            <main>
                <Outlet />
            </main>
        </>
    );
};
export default RootLayout;