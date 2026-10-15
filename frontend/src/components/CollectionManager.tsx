import React, { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { CollectionItem } from "../types";

export const CollectionManager: React.FC = () => {
  const { hasRole } = useAuth();
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canCreate = hasRole("operator");
  const canDelete = hasRole("admin");

  const loadCollections = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.listCollections();
      setCollections(res.items);
    } catch (err: any) {
      setError(err.message || "Failed to load collections.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCollections();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Collection name is required.");
      return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      setError("Collection name must contain only letters, numbers, underscores, and hyphens.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.createCollection(name, description);
      setSuccess(`Collection '${name}' created successfully.`);
      setName("");
      setDescription("");
      await loadCollections();
    } catch (err: any) {
      setError(err.message || "Failed to create collection.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (collectionName: string) => {
    if (!window.confirm(`Delete collection '${collectionName}'? This action cannot be undone.`)) {
      return;
    }
    if (collectionName === "default") {
      setError("Cannot delete the default collection.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await apiClient.deleteCollection(collectionName);
      setSuccess(`Collection '${collectionName}' deleted.`);
      await loadCollections();
    } catch (err: any) {
      setError(err.message || "Failed to delete collection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section-container">
      <h2>Collection Management</h2>
      <p className="section-desc">
        Create, list, and manage document collections. Collections organize documents for scoped retrieval and access control.
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Create Collection */}
      <div className="card">
        <h3>Create New Collection</h3>
        <form onSubmit={handleCreate} className="form-grid">
          <div className="form-group">
            <label htmlFor="coll-name">Collection Name *</label>
            <input
              id="coll-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-collection"
              pattern="^[a-zA-Z0-9_-]+$"
              disabled={!canCreate || loading}
              required
            />
            <small className="form-hint">Letters, numbers, underscores, and hyphens only.</small>
          </div>

          <div className="form-group">
            <label htmlFor="coll-desc">Description</label>
            <textarea
              id="coll-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={2}
              disabled={!canCreate || loading}
              maxLength={500}
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!canCreate || loading}
            >
              {loading ? "Creating..." : "Create Collection"}
            </button>
            {!canCreate && <span className="role-hint">Requires Operator role</span>}
          </div>
        </form>
      </div>

      {/* Collections List */}
      <div className="card mt-4">
        <h3>Existing Collections</h3>
        {loading ? (
          <div className="loading">Loading collections...</div>
        ) : collections.length === 0 ? (
          <div className="empty-state">No collections found. Create one above.</div>
        ) : (
          <div className="collections-table-container">
            <table className="collections-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Documents</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {collections.map((coll) => (
                  <tr key={coll.name}>
                    <td>
                      <span className={`coll-name ${coll.name === "default" ? "default-badge" : ""}`}>
                        {coll.name}
                        {coll.name === "default" && <span className="badge badge-info">Default</span>}
                      </span>
                    </td>
                    <td>{coll.description || <span className="text-muted">—</span>}</td>
                    <td>{coll.document_count}</td>
                    <td>{new Date(coll.created_at).toLocaleString()}</td>
                    <td>
                      {canDelete && coll.name !== "default" && (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(coll.name)}
                          disabled={loading}
                        >
                          Delete
                        </button>
                      )}
                      {!canDelete && coll.name !== "default" && (
                        <span className="role-hint">Admin required</span>
                      )}
                      {coll.name === "default" && <span className="text-muted">Protected</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};