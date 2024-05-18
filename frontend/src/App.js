import 'bootstrap/dist/css/bootstrap.min.css';
import './Styles.css';
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import RootLayout from "./components/RootLayout";
import Notes, { loadNotes, loadArchivedNotes } from "./components/Notes/Notes";
import ErrorPage from "./components/ErrorPage";
import Login from "./components/Login";
import ProtectedComponent from "./components/ProtectedComponent";
import SignUp from "./components/SignUp";
import NoteForm, { loadNoteDetail, loadTagsAndCategories } from './components/Notes/NoteForm';

const router = createBrowserRouter([{
  path: '/',
  element: <RootLayout />,
  errorElement: <ErrorPage />,
  children: [
    { index: true, element: <Login /> },
    { path: 'signup', element: <SignUp /> },
    {
      path: 'notes', element: <ProtectedComponent />,
      children: [
        { index: true, element: <Notes />, loader: loadNotes },
        { path: 'archived', element: <Notes />, loader: loadArchivedNotes },
        { path: 'new', element: <NoteForm />, loader: loadTagsAndCategories },
        { path: ':noteId/edit', element: <NoteForm />, loader: loadNoteDetail },
      ]
    },
  ]
}]);


function App() {
  return <RouterProvider router={router} />
}

export default App;