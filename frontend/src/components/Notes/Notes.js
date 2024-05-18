import { NavLink, useLoaderData } from 'react-router-dom';
import Note from './Note';
import { useEffect, useState } from 'react';
import { sendRequest } from '../../utils/HttpRequest';


const Notes = () => {
  const loadedNotes = useLoaderData();
  const [notes, setNotes] = useState(loadedNotes);
  useEffect(() => {
    setNotes(loadedNotes);
  }, [loadedNotes]);
  const deleteNote = async (noteId) => {
    await sendRequest('DELETE', `/notes/${noteId}/`);
    setNotes(notes.filter(note => note.id !== noteId));
  };

  return (
    <div className="container">
      <h1 className="mt-4 text-center text-white">Notes</h1>
      <p className="text-center">
        <NavLink to="/notes/new/" className="btn btn-success me-2 mt-3 text-center">Add Note</NavLink>
      </p>
      <div className="row row-cols-1 row-cols-md-3 g-4 mt-3">
        {notes.map((note) => (
          <Note key={note.id} note={note} deleteNote={deleteNote} />
        ))}
      </div>
    </div>
  );
};


export default Notes;


export async function loadArchivedNotes() {
  return await sendRequest('GET', '/notes/?archived=1');
}

export async function loadNotes() {
  return await sendRequest('GET', '/notes/?archived=0');
}