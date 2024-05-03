import React, { useState } from 'react';
import { sendRequest } from '../../utils/HttpRequest';
import { useLoaderData, useNavigate } from 'react-router-dom';

const NoteForm = () => {
    const navigate = useNavigate();
    const loaderData = useLoaderData();
    const { categories, tags } = loaderData;
    let { noteDetails } = loaderData;
    if (!noteDetails) {
        noteDetails = {
            title: '',
            content: '',
            tags: [],
            categories: [],
        };
    }

    const [title, setTitle] = useState(noteDetails.title);
    const [content, setContent] = useState(noteDetails.content);
    const [selectedTags, setSelectedTags] = useState(noteDetails.tags.map(tag => tag.id));
    const [selectedCategories, setSelectedCategories] = useState(noteDetails.categories.map(category => category.id));
    const archived = noteDetails.archived || false;


    const handleSubmit = async (e) => {
        e.preventDefault();
        const note = {
            title,
            content,
            tags: selectedTags,
            categories: selectedCategories
        };
        let httpMethod = 'POST';
        let url = '/notes/';
        if (noteDetails.id) {
            httpMethod = 'PUT';
            url += noteDetails.id + '/';
        }
        await sendRequest(httpMethod, url, note);
        navigate(archived ? '/notes/archived/' : '/notes/');
    };


    return (
        <div className="container d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
            <div className="card p-4" style={{ width: '500px' }}>
                <form onSubmit={handleSubmit}>
                    <div className="mb-3">
                        <label htmlFor="title" className="form-label">Title</label>
                        <input type="text" className="form-control" id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
                    </div>
                    <div className="mb-3">
                        <label htmlFor="content" className="form-label">Content</label>
                        <textarea className="form-control" id="content" value={content} onChange={(e) => setContent(e.target.value)} />
                    </div>
                    <div className="mb-3">
                        <label htmlFor="tags" className="form-label">Tags</label>
                        <select multiple className="form-select" id="tags" value={selectedTags} onChange={(e) => setSelectedTags(Array.from(e.target.selectedOptions, option => parseInt(option.value)))}>
                            {tags && tags.map(tag => (
                                <option key={tag.id} value={tag.id}>{tag.name}</option>
                            ))}
                        </select>
                        <div>
                            {selectedTags.map(selectedTagId => {
                                const tag = tags.find(tag => tag.id === selectedTagId);
                                return (
                                    <span key={tag.id} className="badge bg-secondary me-2">{tag.name}</span>
                                );
                            })}
                        </div>
                    </div>
                    <div className="mb-3">
                        <label htmlFor="categories" className="form-label">Categories</label>
                        <select multiple className="form-select" id="categories" value={selectedCategories} onChange={(e) => setSelectedCategories(Array.from(e.target.selectedOptions, option => parseInt(option.value)))}>
                            {categories && categories.map(category => (
                                <option key={category.id} value={category.id}>{category.name}</option>
                            ))}
                        </select>
                        <div>
                            {selectedCategories.map(selectedCategoryId => {
                                const category = categories.find(category => category.id === selectedCategoryId);
                                return (
                                    <span key={category.id} className="badge bg-secondary me-2">{category.name}</span>
                                );
                            })}
                        </div>
                    </div>
                    <button type="submit" className="btn btn-primary">Submit</button>
                </form>
            </div>
        </div>
    );
};

export default NoteForm;


export const loadTagsAndCategories = async () => {
    const categories = await sendRequest('GET', '/categories/');
    const tags = await sendRequest('GET', '/tags/');
    return { categories, tags };
};

export const loadNote = async () => {
    return await sendRequest('GET', '/notes//');
};
export const loadNoteDetail = async ({ request, params }) => {
    const { categories, tags } = await loadTagsAndCategories();
    const noteDetails = await sendRequest('GET', `/notes/${params.noteId}/`);
    return { categories, tags, noteDetails };
};