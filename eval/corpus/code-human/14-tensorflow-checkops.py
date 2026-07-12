    Decorator that adds the appropriate docstring to the function for symbol
    `sym`.
  """

  def _decorator(func):
    """Generated decorator that adds the appropriate docstring to the function for symbol `sym`.

    Args:
      func: Function for a TensorFlow op

    Returns:
      Version of `func` with documentation attached.
    """
    opname = func.__name__
    cap_sym_name = sym_name.capitalize()

    func.__doc__ = """
    Assert the condition `x {sym}` holds element-wise.

    When running in graph mode, you should add a dependency on this operation
    to ensure that it runs. Example of adding a dependency to an operation:

    ```python
    with tf.control_dependencies([tf.debugging.{opname}(x, y)]):
      output = tf.reduce_sum(x)
    ```

    {sym_name} means, for every element `x[i]` of `x`, we have `x[i] {sym}`.
    If `x` is empty this is trivially satisfied.

    Args:
      x:  Numeric `Tensor`.
      data:  The tensors to print out if the condition is False.  Defaults to
        error message and first few entries of `x`.
      summarize: Print this many entries of each tensor.
      message: A string to prefix to the default message.
      name: A name for this operation (optional).  Defaults to "{opname}".

    Returns:
      Op that raises `InvalidArgumentError` if `x {sym}` is False.
      @compatibility(eager)
        returns None
      @end_compatibility

    Raises:
      InvalidArgumentError: if the check can be performed immediately and
        `x {sym}` is False. The check can be performed immediately during 
        eager execution or if `x` is statically known.
    """.format(
        sym=sym, sym_name=cap_sym_name, opname=opname)
    return func

  return _decorator


def _binary_assert_doc(sym):
  """Common docstring for most of the v1 assert_* ops that compare two tensors element-wise.

  Args:
    sym: Binary operation symbol, i.e. "=="

  Returns:
    Decorator that adds the appropriate docstring to the function for
  symbol `sym`.
  """

  def _decorator(func):
    """Generated decorator that adds the appropriate docstring to the function for symbol `sym`.

    Args:
      func: Function for a TensorFlow op

    Returns:
      A version of `func` with documentation attached.
    """
    opname = func.__name__

    func.__doc__ = """
    Assert the condition `x {sym} y` holds element-wise.

    This condition holds if for every pair of (possibly broadcast) elements
    `x[i]`, `y[i]`, we have `x[i] {sym} y[i]`.
    If both `x` and `y` are empty, this is trivially satisfied.

    When running in graph mode, you should add a dependency on this operation
    to ensure that it runs. Example of adding a dependency to an operation:

    ```python
    with tf.control_dependencies([tf.compat.v1.{opname}(x, y)]):
      output = tf.reduce_sum(x)
    ```

    Args:
      x:  Numeric `Tensor`.
      y:  Numeric `Tensor`, same dtype as and broadcastable to `x`.
      data:  The tensors to print out if the condition is False.  Defaults to
        error message and first few entries of `x`, `y`.
      summarize: Print this many entries of each tensor.
      message: A string to prefix to the default message.
      name: A name for this operation (optional).  Defaults to "{opname}".

    Returns:
      Op that raises `InvalidArgumentError` if `x {sym} y` is False.
      @compatibility(eager)
        returns None
      @end_compatibility

    Raises:
      InvalidArgumentError: if the check can be performed immediately and
        `x {sym} y` is False. The check can be performed immediately during 
        eager execution or if `x` and `y` are statically known.
    """.format(
        sym=sym, opname=opname)
    return func

  return _decorator


def _make_assert_msg_data(sym, x, y, summarize, test_op):
  """Subroutine of _binary_assert that generates the components of the default error message when running in eager mode.

  Args:
    sym: Mathematical symbol for the test to apply to pairs of tensor elements,
      i.e. "=="
    x: First input to the assertion after applying `convert_to_tensor()`
    y: Second input to the assertion
    summarize: Value of the "summarize" parameter to the original assert_* call;
      tells how many elements of each tensor to print.
    test_op: TensorFlow op that returns a Boolean tensor with True in each
      position where the assertion is satisfied.

  Returns:
    List of tensors and scalars that, when stringified and concatenated,
    will produce the error message string.
  """
  # Prepare a message with first elements of x and y.
  data = []

  data.append('Condition x %s y did not hold.' % sym)

  if summarize > 0:
    if x.shape == y.shape and x.shape.as_list():
      # If the shapes of x and y are the same (and not scalars),
      # Get the values that actually differed and their indices.
      # If shapes are different this information is more confusing
      # than useful.
      mask = math_ops.logical_not(test_op)
      indices = array_ops.where(mask)
      indices_np = indices.numpy()
      x_vals = array_ops.boolean_mask(x, mask)
      y_vals = array_ops.boolean_mask(y, mask)
      num_vals = min(summarize, indices_np.shape[0])
      data.append('Indices of first %d different values:' % num_vals)
      data.append(indices_np[:num_vals])
      data.append('Corresponding x values:')
      data.append(x_vals.numpy().reshape((-1,))[:num_vals])
      data.append('Corresponding y values:')
      data.append(y_vals.numpy().reshape((-1,))[:num_vals])

    # reshape((-1,)) is the fastest way to get a flat array view.
