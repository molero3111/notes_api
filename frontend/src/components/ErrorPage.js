import { useRouteError } from "react-router-dom";

const ErrorPage = () => {
    const error = useRouteError();

    let title = 'An error occurred!';
    let message = 'Something went wrong.';

    if (error.status === 500) {
        message = error.data.message;
    } else if (error.status === 404) {
        title = 'Not found!';
        message = 'Could not find resource or page.'
    }

    return (
        <>
            <h1>{title}</h1>
            <h2>{message}</h2>
        </>
    );
};

export default ErrorPage;