// ====================
// LocalStorage Utility Module
// ====================

const StorageUtil = {
    /**
     * Get item from localStorage and parse as JSON
     * @param {string} key - The storage key
     * @param {*} defaultValue - Default value if key doesn't exist
     * @returns {*} Parsed value or default
     */
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error(`Error reading from localStorage (${key}):`, error);
            return defaultValue;
        }
    },

    /**
     * Set item in localStorage as JSON
     * @param {string} key - The storage key
     * @param {*} value - Value to store
     * @returns {boolean} Success status
     */
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error(`Error writing to localStorage (${key}):`, error);
            return false;
        }
    },

    /**
     * Get raw string from localStorage
     * @param {string} key - The storage key
     * @param {string} defaultValue - Default value if key doesn't exist
     * @returns {string} Raw value or default
     */
    getRaw(key, defaultValue = null) {
        return localStorage.getItem(key) || defaultValue;
    },

    /**
     * Set raw string in localStorage
     * @param {string} key - The storage key
     * @param {string} value - Value to store
     * @returns {boolean} Success status
     */
    setRaw(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (error) {
            console.error(`Error writing to localStorage (${key}):`, error);
            return false;
        }
    },

    /**
     * Remove item from localStorage
     * @param {string} key - The storage key
     */
    remove(key) {
        localStorage.removeItem(key);
    },

    /**
     * Clear all localStorage
     */
    clear() {
        localStorage.clear();
    },

    /**
     * Check if key exists in localStorage
     * @param {string} key - The storage key
     * @returns {boolean}
     */
    has(key) {
        return localStorage.getItem(key) !== null;
    }
};
