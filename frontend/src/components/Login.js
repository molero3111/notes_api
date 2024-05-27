import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { login } from '../store/Authentication/AuthActions';
import { useNavigate } from 'react-router-dom';
import { sendRequest } from '../utils/HttpRequest';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loginError, setLogingError] = useState(false);
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        try {
            const responseData = await sendRequest('POST', '/login/', {
                username,
                password
            }, false);
            const token = responseData.token;
            dispatch(login(token));
            localStorage.setItem('token', token);
            navigate('/notes');
        } catch (error) {
            setLogingError(true);
            console.error('Error logging in:', error);
        }
    };

    return (
        <div className="container d-flex justify-content-center align-items-center" style={{ minHeight: '70vh' }}>
            <div className="card p-4" style={{ width: '400px' }}>
                <h2 className="text-center mb-4">Login</h2>
                <form onSubmit={handleLogin}>
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
                    <button type="submit" className="btn btn-primary">Login</button>
                    {loginError && <p className='text-danger text-center' >Invalid credentials</p>}
                </form>
            </div>
        </div>
    );
};

export default Login;

