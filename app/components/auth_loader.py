"""Auth loader component that runs on every page load."""
import streamlit as st
import streamlit.components.v1 as components
import os


def load_auth_on_page_load():
    """Load authentication from localStorage on page load.
    This component should be placed at the top of every page.
    """
    # Only run if not already authenticated
    if not st.session_state.get("authenticated", False):
        # Check URL params first (might have been set by previous run)
        query_params = st.query_params
        if query_params.get("_auth_loaded") == "1":
            # Already processed, don't inject script again
            return
        
        # Use inline script with components.html
        # The script accesses parent window to get localStorage
        html = """
        <script>
        (function() {
            // Get the correct window object (parent if in iframe, self otherwise)
            let win = window;
            try {
                if (window.parent !== window && window.parent !== null) {
                    win = window.parent;
                }
            } catch (e) {
                // Cross-origin error, use current window
                win = window;
            }
            
            function checkAndRestoreAuth() {
                try {
                    // Check localStorage for auth data
                    const authData = win.localStorage.getItem('auth_data');
                    console.log('[Auth Loader] Checking localStorage, found:', authData ? 'yes' : 'no');
                    if (authData) {
                        const data = JSON.parse(authData);
                        console.log('[Auth Loader] Auth data:', data);
                        if (data.authenticated && data.user_id && data.user_email) {
                            // Check if we've already set the params
                            const url = new URL(win.location.href);
                            if (!url.searchParams.has('_auth_loaded')) {
                                console.log('[Auth Loader] Setting URL params and reloading...');
                                // Set URL params to pass to Python
                                url.searchParams.set('_auth_user_id', String(data.user_id));
                                url.searchParams.set('_auth_user_email', encodeURIComponent(data.user_email));
                                url.searchParams.set('_auth_authenticated', 'true');
                                url.searchParams.set('_auth_loaded', '1');
                                win.history.replaceState({}, '', url);
                                // Reload to let Python read the params
                                setTimeout(() => {
                                    console.log('[Auth Loader] Reloading page...');
                                    win.location.reload();
                                }, 100);
                            } else {
                                console.log('[Auth Loader] URL params already set, skipping');
                            }
                        }
                    }
                } catch (e) {
                    console.error('[Auth Loader] Error:', e);
                }
            }
            
            // Run immediately
            console.log('[Auth Loader] Script loaded, readyState:', win.document.readyState);
            if (win.document.readyState === 'loading') {
                win.document.addEventListener('DOMContentLoaded', checkAndRestoreAuth);
            } else {
                // Small delay to ensure Streamlit is ready
                setTimeout(checkAndRestoreAuth, 150);
            }
        })();
        </script>
        """
        # Use components.html - it will run in iframe but can access parent
        components.html(html, height=0, width=0)


def check_and_restore_from_url():
    """Check URL params and restore auth state if present."""
    query_params = st.query_params
    
    # Check for auth params
    if query_params.get("_auth_loaded") == "1":
        user_id = query_params.get("_auth_user_id")
        user_email = query_params.get("_auth_user_email")
        if user_id and user_email and not st.session_state.get("authenticated", False):
            try:
                import urllib.parse
                st.session_state.authenticated = True
                st.session_state.user_id = int(user_id)
                st.session_state.user_email = urllib.parse.unquote(user_email)
                # Clear the auth params but keep others
                new_params = {k: v for k, v in query_params.items() if not k.startswith('_auth_')}
                st.query_params.clear()
                if new_params:
                    st.query_params.update(new_params)
                return True
            except (ValueError, TypeError) as e:
                print(f"Error restoring auth: {e}")
    
    return False

