import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { login } from '../store/Authentication/AuthActions';
import { useNavigate } from 'react-router-dom';
import { sendRequest } from '../utils/HttpRequest';

const SignUp = () => {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [signupError, setSignupError] = useState(false);
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const handleSignup = async (e) => {
        e.preventDefault();
        try {
            const responseData = await sendRequest('POST', '/register/', {
                username,
                email,
                password
            }, false);
            const token = responseData.token;
            dispatch(login(token));
            localStorage.setItem('token', token);
            navigate('/notes');
        } catch (error) {
            console.log('error is ', error);
            setSignupError(true);
        }
    };

    return (
        <div className="container d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
            <div className="card p-4" style={{ width: '400px' }}>
                <h2 className="text-center mb-4">Sign Up</h2>
                <form onSubmit={handleSignup}>
                    <div className="mb-3">
                        <label htmlFor="username" className="form-label">Username</label>
                        <input
                            type="text"
                            className="form-control"
                            id="username"
                            placeholder="Enter username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>
                    <div className="mb-3">
                        <label htmlFor="email" className="form-label">Email</label>
                        <input
                            type="text"
                            className="form-control"
                            id="email"
                            placeholder="Enter email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>
                    <div className="mb-3">
                        <label htmlFor="password" className="form-label">Password</label>
                        <input
                            type="password"
                            className="form-control"
                            id="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary">Sign Up</button>
                    {signupError && <p className='text-danger text-center' >Error during signup, please check you data and try again.</p>}
                </form>
            </div>
        </div>
    );
};

export default SignUp;

