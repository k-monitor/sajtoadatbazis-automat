function getCookieValue(cookieName) {
    const name = cookieName + "=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i].trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length, cookie.length);
        }
    }
    return null;
}

import { useLazyFetch, useFetch } from '#app';

export function useAuthLazyFetch(url, options = {}) {
    const cookieName = 'PHPSESSID';
    const cookieValue = getCookieValue(cookieName);
    
    const headers = {
        ...options.headers,
        'Authorization': `${cookieValue}`,
    };

    return useLazyFetch(url, {
        ...options,
        headers,
    });
}

export async function useAuthFetch(url, options = {}) {
    const cookieName = 'PHPSESSID';
    const cookieValue = getCookieValue(cookieName);
    
    const headers = {
        ...options.headers,
        'Authorization': `${cookieValue}`,
    };

    return await useFetch(url, {
        ...options,
        headers,
    });
}

export function $authFetch(url, options = {}) {
    const cookieName = 'PHPSESSID';
    const cookieValue = getCookieValue(cookieName);
    
    const headers = {
        ...options.headers,
        'Authorization': `${cookieValue}`,
    };

    return $fetch(url, {
        ...options,
        headers,
    });
}
