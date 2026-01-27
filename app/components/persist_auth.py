"""Persistent authentication using browser localStorage."""
import streamlit as st
import streamlit.components.v1 as components
import json
import urllib.parse


def save_auth_to_storage(user_id: int, user_email: str):
    """Save authentication info to browser localStorage."""
    auth_data = {
        "authenticated": True,
        "user_id": user_id,
        "user_email": user_email
    }
    
    html = f"""
    <script>
        localStorage.setItem('auth_data', JSON.stringify({json.dumps(auth_data)}));
        console.log('Auth data saved to localStorage');
    </script>
    """
    components.html(html, height=0, width=0)


def clear_auth_storage():
    """Clear authentication info from browser localStorage."""
    html = """
    <script>
        localStorage.removeItem('auth_data');
        console.log('Auth data cleared from localStorage');
    </script>
    """
    components.html(html, height=0, width=0)


def restore_auth_state():
    """Restore authentication state from localStorage if available."""
    # First, check query params (set by JavaScript on previous run)
    query_params = st.query_params
    
    # If auth data is in URL params, restore it immediately
    if query_params.get("_auth_restored") == "1":
        user_id = query_params.get("_auth_user_id")
        user_email = query_params.get("_auth_user_email")
        if user_id and user_email:
            try:
                st.session_state.authenticated = True
                st.session_state.user_id = int(user_id)
                st.session_state.user_email = urllib.parse.unquote(user_email)
                st.session_state.auth_restored = True
                # Clear auth params but keep others
                new_params = {k: v for k, v in query_params.items() if not k.startswith('_auth_')}
                st.query_params.clear()
                if new_params:
                    st.query_params.update(new_params)
                return
            except (ValueError, TypeError) as e:
                print(f"Error restoring auth state: {e}")
    
    # If not already restored and not authenticated, try to restore from localStorage
    if not st.session_state.get("auth_restored", False) and not st.session_state.authenticated:
        # Use JavaScript to read from localStorage and set URL params
        html = """
        <script>
        (function() {
            const authData = localStorage.getItem('auth_data');
            if (authData) {
                try {
                    const data = JSON.parse(authData);
                    if (data.authenticated && data.user_id && data.user_email) {
                        const url = new URL(window.location);
                        // Only set if not already set
                        if (!url.searchParams.has('_auth_restored')) {
                            url.searchParams.set('_auth_user_id', data.user_id);
                            url.searchParams.set('_auth_user_email', encodeURIComponent(data.user_email));
                            url.searchParams.set('_auth_authenticated', 'true');
                            url.searchParams.set('_auth_restored', '1');
                            window.history.replaceState({}, '', url);
                            // Force a page reload to trigger Python to read the params
                            window.location.reload();
                        }
                    }
                } catch (e) {
                    console.error('Error parsing auth data:', e);
                }
            }
        })();
        </script>
        """
        components.html(html, height=0, width=0)
        st.session_state.auth_restored = True

