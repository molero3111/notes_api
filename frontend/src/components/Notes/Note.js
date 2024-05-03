import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { sendRequest } from '../../utils/HttpRequest';


const Note = ({ note, deleteNote }) => {
  const navigate = useNavigate();
  const archiveNote = async () => {
    await sendRequest('PUT', `/notes/${note.id}/`, {
      archived: !note.archived
    });
    navigate(note.archived ? '/notes/archived/' : '/notes/');
  };
  return (
    <div className="col" key={note.id}>
      <div className="card">
        <div className="card-body text-center">
          <h5 className="card-title">{note.title}</h5>
          <p className="card-text">{note.content}</p>
          <div className="mb-3">
            <h6 className="text-dark">Categories</h6>
            {note.categories.map((category) => (
              <span key={category.id} className="badge bg-dark me-2">
                {category.name}
              </span>
            ))}
          </div>
          <div>
            <h6 className="text-secondary">Tags</h6>
            {note.tags.map((tag) => (
              <span key={tag.id} className="badge bg-light text-secondary me-2">
                {tag.name}
              </span>
            ))}
          </div>
          <NavLink to={`/notes/${note.id}/edit`} className="btn btn-primary me-2 mt-3 text-center">Update</NavLink>
          <button className="btn btn-secondary me-2 mt-3" onClick={archiveNote}>{note.archived ? 'Unarchive' : 'Archive'}</button>
          <button className="btn btn-danger me-2 mt-3" onClick={() => deleteNote(note.id)}>Delete</button>
        </div>
      </div>
    </div>
  );
};

export default Note;